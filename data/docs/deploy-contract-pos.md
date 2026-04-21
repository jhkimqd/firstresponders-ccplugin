# Deploying a Smart Contract on Polygon PoS

## Overview

Polygon PoS (Proof of Stake) is an EVM-compatible sidechain that offers faster and cheaper transactions than Ethereum mainnet. Deploying a smart contract on Polygon PoS is nearly identical to deploying on Ethereum, since Polygon PoS is fully EVM-compatible.

## Prerequisites

- A wallet with POL (formerly MATIC) tokens for gas fees
- An RPC endpoint for Polygon PoS (public or private)
- Your compiled smart contract (Solidity)
- A deployment tool: Hardhat, Foundry, or Remix

## Network Details

| Parameter | Value |
|-----------|-------|
| Network Name | Polygon PoS |
| Chain ID | 137 |
| Currency | POL |
| RPC URL | https://polygon-rpc.com |
| Block Explorer | https://polygonscan.com |
| Testnet (Amoy) Chain ID | 80002 |
| Testnet RPC | https://rpc-amoy.polygon.technology |

## Deploying with Hardhat

### 1. Install Hardhat

```bash
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
npx hardhat init
```

### 2. Configure Polygon Network

Add Polygon to your `hardhat.config.js`:

```javascript
require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.24",
  networks: {
    polygon: {
      url: "https://polygon-rpc.com",
      chainId: 137,
      accounts: [process.env.PRIVATE_KEY],
    },
    amoy: {
      url: "https://rpc-amoy.polygon.technology",
      chainId: 80002,
      accounts: [process.env.PRIVATE_KEY],
    },
  },
};
```

### 3. Write a Deployment Script

Create `scripts/deploy.js`:

```javascript
const { ethers } = require("hardhat");

async function main() {
  const Contract = await ethers.getContractFactory("MyContract");
  const contract = await Contract.deploy();
  await contract.waitForDeployment();
  console.log("Contract deployed to:", await contract.getAddress());
}

main().catch(console.error);
```

### 4. Deploy

```bash
# Deploy to Amoy testnet first
npx hardhat run scripts/deploy.js --network amoy

# Deploy to Polygon mainnet
npx hardhat run scripts/deploy.js --network polygon
```

### 5. Verify on Polygonscan

```bash
npx hardhat verify --network polygon DEPLOYED_ADDRESS constructor_arg1 constructor_arg2
```

## Deploying with Foundry

### 1. Install Foundry

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### 2. Deploy

```bash
forge create --rpc-url https://polygon-rpc.com \
  --private-key $PRIVATE_KEY \
  src/MyContract.sol:MyContract \
  --constructor-args arg1 arg2
```

### 3. Verify

```bash
forge verify-contract DEPLOYED_ADDRESS src/MyContract.sol:MyContract \
  --chain polygon \
  --etherscan-api-key $POLYGONSCAN_API_KEY
```

## Deploying with Remix

1. Open [Remix IDE](https://remix.ethereum.org)
2. Write or import your contract
3. Compile the contract
4. In the "Deploy" tab, select "Injected Provider - MetaMask"
5. Make sure MetaMask is connected to Polygon PoS network
6. Click "Deploy" and confirm the transaction in MetaMask

## Gas Fees

Gas fees on Polygon PoS are significantly lower than Ethereum mainnet. A typical contract deployment costs fractions of a cent to a few cents in POL tokens. You can check current gas prices at https://polygonscan.com/gastracker.

## Best Practices

- **Always deploy to testnet first** (Amoy) before mainnet
- **Verify your contracts** on Polygonscan for transparency
- **Use a private RPC endpoint** for production deployments (Alchemy, Infura, QuickNode)
- **Secure your private keys** — use environment variables or hardware wallets, never hardcode them
- **Test thoroughly** — Polygon PoS has 2-second block times, so testing is fast
