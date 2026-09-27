const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Adaptive Consensus & Node Registry Suite", function () {
  let owner, oracle, attacker;
  let nodes = [];
  let registry, consensus;

  beforeEach(async function () {
    const signers = await ethers.getSigners();
    owner = signers[0];
    oracle = signers[1];
    attacker = signers[2];
    nodes = signers.slice(3, 11); // 8 nodes

    // Deploy NodeRegistry
    const NodeRegistryFactory = await ethers.getContractFactory("NodeRegistry");
    registry = await NodeRegistryFactory.deploy(owner.address);
    await registry.waitForDeployment();

    // Deploy AdaptiveConsensus
    const AdaptiveConsensusFactory = await ethers.getContractFactory("AdaptiveConsensus");
    consensus = await AdaptiveConsensusFactory.deploy(await registry.getAddress(), owner.address);
    await consensus.waitForDeployment();

    // Authorize Oracle in AdaptiveConsensus
    await consensus.setOracleController(oracle.address);

    // Register all nodes in NodeRegistry
    for (let i = 0; i < nodes.length; i++) {
      await registry.registerNode(nodes[i].address, `Device_ESP32_${i}`, 950); // 0.95 rep
    }
  });

  it("Should properly register nodes and verify eligibility", async function () {
    expect(await registry.totalRegisteredNodes()).to.equal(nodes.length);
    expect(await registry.isNodeEligible(nodes[0].address)).to.be.true;

    // Slash a node and check eligibility
    await registry.slashNode(nodes[0].address, "Double-signing detected");
    expect(await registry.isNodeEligible(nodes[0].address)).to.be.false;
  });

  it("Should reject epoch committee scheduling if size < 4 (BFT Violation)", async function () {
    const smallCommittee = [nodes[1].address, nodes[2].address, nodes[3].address]; // size 3
    await expect(
      consensus.connect(oracle).setEpochCommittee(1, smallCommittee, nodes[1].address)
    ).to.be.revertedWith("BFT Violation: Committee size must be >= 4 (3f + 1)");
  });

  it("Should schedule epoch and calculate correct quorum threshold (floor(2/3*K) + 1)", async function () {
    const committee = [nodes[1].address, nodes[2].address, nodes[3].address, nodes[4].address, nodes[5].address]; // size 5
    // Quorum for 5 nodes: floor(2/3 * 5) + 1 = 3 + 1 = 4
    await expect(consensus.connect(oracle).setEpochCommittee(1, committee, nodes[1].address))
      .to.emit(consensus, "EpochScheduled")
      .withArgs(1, 5, nodes[1].address, 4);

    const scheduled = await consensus.getEpochCommittee(1);
    expect(scheduled.quorumThreshold).to.equal(4);
    expect(scheduled.leader).to.equal(nodes[1].address);
  });

  it("Should commit block successfully when valid quorum signatures are submitted", async function () {
    const committee = [nodes[1], nodes[2], nodes[3], nodes[4], nodes[5]];
    const committeeAddrs = committee.map((n) => n.address);
    const leader = committee[0];

    // Schedule epoch 1
    await consensus.connect(oracle).setEpochCommittee(1, committeeAddrs, leader.address);

    const blockNumber = 1;
    const stateRoot = ethers.keccak256(ethers.toUtf8Bytes("state_root_hash_epoch_1"));
    const telemetryHash = ethers.keccak256(ethers.toUtf8Bytes("telemetry_payload_hash_1"));

    // Raw hash: keccak256(abi.encodePacked(epochId, blockNumber, stateRoot, telemetryHash))
    const rawHash = ethers.solidityPackedKeccak256(
      ["uint256", "uint256", "bytes32", "bytes32"],
      [1, blockNumber, stateRoot, telemetryHash]
    );

    // Collect 4 signatures (quorum threshold for K=5 is 4)
    const signatures = [];
    for (let i = 0; i < 4; i++) {
      const sig = await committee[i].signMessage(ethers.getBytes(rawHash));
      signatures.push(sig);
    }

    // Submit block commitment
    await expect(
      consensus.commitBlock(1, blockNumber, stateRoot, telemetryHash, signatures)
    )
      .to.emit(consensus, "BlockCommitted")
      .withArgs(1, blockNumber, leader.address, stateRoot, telemetryHash, 4);

    expect(await consensus.latestBlockNumber()).to.equal(1);
  });

  it("Should reject block if signatures are below quorum threshold", async function () {
    const committee = [nodes[1], nodes[2], nodes[3], nodes[4], nodes[5]];
    const committeeAddrs = committee.map((n) => n.address);
    const leader = committee[0];

    await consensus.connect(oracle).setEpochCommittee(1, committeeAddrs, leader.address);

    const blockNumber = 1;
    const stateRoot = ethers.keccak256(ethers.toUtf8Bytes("state_root_hash_epoch_1"));
    const telemetryHash = ethers.keccak256(ethers.toUtf8Bytes("telemetry_payload_hash_1"));

    const rawHash = ethers.solidityPackedKeccak256(
      ["uint256", "uint256", "bytes32", "bytes32"],
      [1, blockNumber, stateRoot, telemetryHash]
    );

    // Only collect 3 signatures (needs 4)
    const signatures = [];
    for (let i = 0; i < 3; i++) {
      const sig = await committee[i].signMessage(ethers.getBytes(rawHash));
      signatures.push(sig);
    }

    await expect(
      consensus.commitBlock(1, blockNumber, stateRoot, telemetryHash, signatures)
    ).to.be.revertedWith("Insufficient signatures supplied");
  });
});
