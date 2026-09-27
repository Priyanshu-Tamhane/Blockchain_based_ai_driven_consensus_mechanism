const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log(`[Deployer] Deploying contracts with address: ${deployer.address}`);

  // Deploy NodeRegistry
  const NodeRegistry = await ethers.getContractFactory("NodeRegistry");
  const registry = await NodeRegistry.deploy(deployer.address);
  await registry.waitForDeployment();
  const registryAddress = await registry.getAddress();
  console.log(`[NodeRegistry] Deployed to: ${registryAddress}`);

  // Deploy AdaptiveConsensus
  const AdaptiveConsensus = await ethers.getContractFactory("AdaptiveConsensus");
  const consensus = await AdaptiveConsensus.deploy(registryAddress, deployer.address);
  await consensus.waitForDeployment();
  const consensusAddress = await consensus.getAddress();
  console.log(`[AdaptiveConsensus] Deployed to: ${consensusAddress}`);

  // Set Deployer as initial authorized Oracle Controller
  await consensus.setOracleController(deployer.address);
  console.log(`[AdaptiveConsensus] Oracle controller set to: ${deployer.address}`);

  // Export deployment info for Python Web3 client
  const deploymentInfo = {
    network: "localhost",
    deployer: deployer.address,
    registryAddress: registryAddress,
    consensusAddress: consensusAddress,
    deployedAt: new Date().toISOString(),
  };

  const contractsDir = path.join(__dirname, "..", "contracts_data");
  if (!fs.existsSync(contractsDir)) {
    fs.mkdirSync(contractsDir, { recursive: true });
  }

  fs.writeFileSync(
    path.join(contractsDir, "deployment.json"),
    JSON.stringify(deploymentInfo, null, 2)
  );

  console.log(`[Export] Deployment info saved to contracts_data/deployment.json`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
