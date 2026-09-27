// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title NodeRegistry
 * @notice Immutable on-chain registry for IoT devices participating in consensus.
 * Tracks device addresses, public identifiers, reputation scores, and slashing status.
 */
contract NodeRegistry is Ownable {
    
    enum NodeStatus { Inactive, Active, Suspended, Slashed }

    struct NodeInfo {
        address nodeAddress;
        string deviceId;
        uint256 reputationScore;  // Scaled by 1000 (e.g. 1000 = 1.0, 600 = 0.60)
        NodeStatus status;
        uint256 registeredAt;
        uint256 blocksValidated;
        uint256 blocksProposed;
    }

    mapping(address => NodeInfo) public nodes;
    address[] public registeredNodes;

    event NodeRegistered(address indexed nodeAddress, string deviceId, uint256 initialReputation);
    event ReputationUpdated(address indexed nodeAddress, uint256 oldReputation, uint256 newReputation);
    event NodeSlashed(address indexed nodeAddress, string reason);
    event NodeStatusChanged(address indexed nodeAddress, NodeStatus newStatus);

    constructor(address initialOwner) Ownable(initialOwner) {}

    /**
     * @notice Registers a new IoT device in the network.
     */
    function registerNode(
        address nodeAddress,
        string calldata deviceId,
        uint256 initialReputation
    ) external onlyOwner {
        require(nodeAddress != address(0), "Invalid address");
        require(nodes[nodeAddress].nodeAddress == address(0), "Node already registered");
        require(initialReputation <= 1000, "Reputation cannot exceed 1000");

        nodes[nodeAddress] = NodeInfo({
            nodeAddress: nodeAddress,
            deviceId: deviceId,
            reputationScore: initialReputation,
            status: NodeStatus.Active,
            registeredAt: block.timestamp,
            blocksValidated: 0,
            blocksProposed: 0
        });

        registeredNodes.push(nodeAddress);
        emit NodeRegistered(nodeAddress, deviceId, initialReputation);
    }

    /**
     * @notice Updates the reputation score of a node based on consensus behavior.
     */
    function updateReputation(address nodeAddress, uint256 newReputation) external onlyOwner {
        require(nodes[nodeAddress].nodeAddress != address(0), "Node not registered");
        require(newReputation <= 1000, "Reputation cannot exceed 1000");

        uint256 oldRep = nodes[nodeAddress].reputationScore;
        nodes[nodeAddress].reputationScore = newReputation;

        emit ReputationUpdated(nodeAddress, oldRep, newReputation);
    }

    /**
     * @notice Slashes a malicious node, revoking its active status and zeroing its reputation.
     */
    function slashNode(address nodeAddress, string calldata reason) external onlyOwner {
        require(nodes[nodeAddress].nodeAddress != address(0), "Node not registered");
        
        nodes[nodeAddress].status = NodeStatus.Slashed;
        nodes[nodeAddress].reputationScore = 0;

        emit NodeSlashed(nodeAddress, reason);
    }

    /**
     * @notice Increments validation activity counters for auditability.
     */
    function recordValidationActivity(address nodeAddress, bool wasLeader) external onlyOwner {
        if (nodes[nodeAddress].nodeAddress != address(0)) {
            nodes[nodeAddress].blocksValidated++;
            if (wasLeader) {
                nodes[nodeAddress].blocksProposed++;
            }
        }
    }

    /**
     * @notice Checks if a node is currently eligible for committee selection.
     */
    function isNodeEligible(address nodeAddress) external view returns (bool) {
        NodeInfo memory node = nodes[nodeAddress];
        return (node.nodeAddress != address(0) &&
                node.status == NodeStatus.Active &&
                node.reputationScore >= 600); // 600 / 1000 = 0.60 trust floor
    }

    /**
     * @notice Returns total number of registered nodes.
     */
    function totalRegisteredNodes() external view returns (uint256) {
        return registeredNodes.length;
    }
}
