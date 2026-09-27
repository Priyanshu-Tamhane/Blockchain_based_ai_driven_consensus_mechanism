// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import "./NodeRegistry.sol";

/**
 * @title AdaptiveConsensus
 * @notice Enforces dynamic committee management and cryptographic quorum verification
 * for the energy-aware adaptive IoT consensus protocol.
 */
contract AdaptiveConsensus is Ownable {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    NodeRegistry public immutable registry;
    address public oracleController;

    struct EpochCommittee {
        uint256 epochId;
        address[] members;
        address leader;
        uint256 quorumThreshold;
        uint256 scheduledAt;
        bool isActive;
    }

    struct BlockCommitment {
        uint256 epochId;
        uint256 blockNumber;
        bytes32 stateRoot;
        bytes32 telemetryHash;
        address proposer;
        uint256 signatureCount;
        uint256 committedAt;
    }

    mapping(uint256 => EpochCommittee) public epochCommittees;
    mapping(uint256 => mapping(address => bool)) public isCommitteeMember;
    mapping(uint256 => BlockCommitment) public committedBlocks;
    uint256 public latestBlockNumber;
    uint256 public currentEpochId;

    event OracleControllerUpdated(address indexed newOracle);
    event EpochScheduled(uint256 indexed epochId, uint256 committeeSize, address indexed leader, uint256 quorumThreshold);
    event BlockCommitted(
        uint256 indexed epochId,
        uint256 indexed blockNumber,
        address indexed proposer,
        bytes32 stateRoot,
        bytes32 telemetryHash,
        uint256 quorumCount
    );

    modifier onlyOracleOrOwner() {
        require(msg.sender == oracleController || msg.sender == owner(), "Caller not authorized oracle or owner");
        _;
    }

    constructor(address _registryAddress, address initialOwner) Ownable(initialOwner) {
        require(_registryAddress != address(0), "Invalid registry address");
        registry = NodeRegistry(_registryAddress);
        oracleController = initialOwner;
    }

    /**
     * @notice Configures the authorized edge AI Oracle address.
     */
    function setOracleController(address _oracleController) external onlyOwner {
        require(_oracleController != address(0), "Invalid oracle address");
        oracleController = _oracleController;
        emit OracleControllerUpdated(_oracleController);
    }

    /**
     * @notice Registers an adaptive committee chosen by the AI Oracle for an epoch.
     * Enforces the Byzantine safety invariant K >= 3f + 1 (min 4 nodes for f=1).
     */
    function setEpochCommittee(
        uint256 epochId,
        address[] calldata members,
        address leader
    ) external onlyOracleOrOwner {
        require(members.length >= 4, "BFT Violation: Committee size must be >= 4 (3f + 1)");
        require(leader != address(0), "Invalid leader address");
        require(!epochCommittees[epochId].isActive, "Epoch already scheduled");

        // Verify leader is in the committee and all members are registered and eligible
        bool leaderInCommittee = false;
        for (uint256 i = 0; i < members.length; i++) {
            address member = members[i];
            require(registry.isNodeEligible(member), "Committee member ineligible or not registered");
            isCommitteeMember[epochId][member] = true;
            if (member == leader) {
                leaderInCommittee = true;
            }
        }
        require(leaderInCommittee, "Leader must be an active committee member");

        // Quorum rule: floor(2/3 * K) + 1
        uint256 quorum = (members.length * 2) / 3 + 1;

        epochCommittees[epochId] = EpochCommittee({
            epochId: epochId,
            members: members,
            leader: leader,
            quorumThreshold: quorum,
            scheduledAt: block.timestamp,
            isActive: true
        });

        currentEpochId = epochId;
        emit EpochScheduled(epochId, members.length, leader, quorum);
    }

    /**
     * @notice Commits a block proposed by the leader with threshold signatures.
     * Verifies that at least quorumThreshold valid, distinct committee signatures are provided.
     */
    function commitBlock(
        uint256 epochId,
        uint256 blockNumber,
        bytes32 stateRoot,
        bytes32 telemetryHash,
        bytes[] calldata signatures
    ) external {
        EpochCommittee storage committee = epochCommittees[epochId];
        require(committee.isActive, "Epoch committee is not active");
        require(blockNumber == latestBlockNumber + 1, "Invalid sequential block number");
        require(signatures.length >= committee.quorumThreshold, "Insufficient signatures supplied");

        // Construct raw payload hash matching off-chain signing format
        bytes32 rawHash = keccak256(abi.encodePacked(epochId, blockNumber, stateRoot, telemetryHash));
        bytes32 ethSignedHash = rawHash.toEthSignedMessageHash();

        address[] memory seenSigners = new address[](signatures.length);
        uint256 validSignaturesCount = 0;

        for (uint256 i = 0; i < signatures.length; i++) {
            address recoveredSigner = ethSignedHash.recover(signatures[i]);
            
            // Check that signer is in the elected committee
            if (isCommitteeMember[epochId][recoveredSigner]) {
                // Ensure no duplicate signatures from the same validator
                bool duplicate = false;
                for (uint256 j = 0; j < validSignaturesCount; j++) {
                    if (seenSigners[j] == recoveredSigner) {
                        duplicate = true;
                        break;
                    }
                }
                if (!duplicate) {
                    seenSigners[validSignaturesCount] = recoveredSigner;
                    validSignaturesCount++;
                }
            }
        }

        require(
            validSignaturesCount >= committee.quorumThreshold,
            "Quorum not achieved: valid unique signatures below threshold"
        );

        // Record block commitment
        committedBlocks[blockNumber] = BlockCommitment({
            epochId: epochId,
            blockNumber: blockNumber,
            stateRoot: stateRoot,
            telemetryHash: telemetryHash,
            proposer: committee.leader,
            signatureCount: validSignaturesCount,
            committedAt: block.timestamp
        });

        latestBlockNumber = blockNumber;

        emit BlockCommitted(
            epochId,
            blockNumber,
            committee.leader,
            stateRoot,
            telemetryHash,
            validSignaturesCount
        );
    }

    /**
     * @notice Returns committee details for a given epoch.
     */
    function getEpochCommittee(uint256 epochId) external view returns (
        address[] memory members,
        address leader,
        uint256 quorumThreshold,
        bool isActive
    ) {
        EpochCommittee storage c = epochCommittees[epochId];
        return (c.members, c.leader, c.quorumThreshold, c.isActive);
    }
}
