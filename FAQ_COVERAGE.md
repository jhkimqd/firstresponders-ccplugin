# Likely Questions by Stakeholder Type — Polygon Ecosystem Chatbot

A reference document for training data, RAG evaluation, and system prompt testing.
Organized by stakeholder persona to guide knowledge base coverage and intent routing.

---

## 1. Node Operators

Operators running full nodes or archive nodes on Polygon PoS.

### Setup & Configuration
- How do I run a Polygon PoS full node?
- What are the minimum hardware requirements for a Polygon PoS node?
- What are the hardware requirements for a Polygon CDK chain node?
- Which client should I use — Bor or Erigon?
- What is the difference between Bor and Heimdall?
- How do I configure Bor and Heimdall to talk to each other?
- What ports do Bor and Heimdall need open?
- How do I enable the JSON-RPC API on my node?
- How do I configure WebSocket support on my node?
- What is the recommended snapshot to bootstrap a new node quickly?
- Where can I download a Polygon PoS chaindata snapshot?
- How do I set up an archive node on Polygon PoS?
- What is the difference between a full node and an archive node on Polygon?
- Can I run a Polygon node on a cloud provider like AWS or GCP?

### Sync & Maintenance
- My node is stuck syncing — how do I diagnose the issue?
- How long does it take to sync a Polygon PoS full node from scratch?
- How do I check if my node is in sync with the network?
- What does "reorg" mean and how do I handle one?
- How do I upgrade my Bor client without downtime?
- How do I upgrade Heimdall to the latest version?
- My node is falling behind on blocks — what should I check?
- How do I prune old state data to recover disk space?
- What log messages indicate a healthy vs unhealthy node?
- How do I monitor my node's health and uptime?
- My node's memory usage keeps growing — what's causing it?
- How do I safely restart Bor without corrupting state?

### Networking & Peers
- How do I add static peers to my Polygon node?
- My node has zero peers — how do I fix this?
- What are the official Polygon bootnodes?
- How do I check how many peers my node has?
- Should I expose my node publicly or keep it internal?

### Chain Data & APIs
- How do I call `eth_getLogs` on my own node?
- Does Polygon PoS support `debug_traceTransaction`?
- Which RPC methods require an archive node vs a full node?
- How do I enable the `txpool` API on my node?
- What is the `eth_getBlockByNumber` rate limit on the public RPC?
- My node returns stale data — is it a caching issue?

---

## 2. Developers

Engineers building dApps, smart contracts, or integrations on Polygon.

### Getting Started
- How do I add Polygon PoS to MetaMask?
- What is the chain ID for Polygon PoS mainnet?
- What is the chain ID for Polygon CDK chains?
- What is the chain ID for Polygon Amoy testnet?
- How do I get testnet MATIC/POL on Amoy?
- What is the difference between Polygon PoS and Polygon CDK?
- Which Polygon network should I build on — PoS or CDK?
- What is Polygon CDK and when should I use it?
- Is Polygon PoS EVM-compatible?
- What Solidity versions are supported on Polygon CDK chains?

### Smart Contracts
- How do I deploy a smart contract on Polygon PoS using Hardhat?
- How do I deploy a smart contract on a Polygon CDK chain?
- How do I verify a smart contract on PolygonScan?
- What is the gas limit per block on Polygon PoS?
- Are there any EVM opcodes not supported on Polygon CDK chains?
- Does Polygon CDK support `CREATE2`?
- How do I estimate gas for a transaction on Polygon?
- My contract deployment fails on CDK but works on PoS — why?
- How do I interact with a deployed contract using ethers.js on Polygon?
- Can I use Foundry to deploy contracts on Polygon?
- What is the block time on Polygon PoS?
- What is the block time on Polygon CDK chains?
- How do I listen for contract events on Polygon using WebSockets?
- What is the `PUSH0` opcode status on Polygon CDK chains?
- How do I use Remix IDE to deploy on Polygon?

### Bridging & Cross-chain
- How does the Polygon PoS bridge work?
- How do I bridge ETH from Ethereum to Polygon PoS?
- How do I bridge tokens from Polygon PoS back to Ethereum?
- What is the withdrawal time from Polygon PoS to Ethereum?
- How does the AggLayer bridge differ from the PoS bridge?
- What is the LxLy bridge?
- Can I bridge any ERC-20 token to Polygon?
- How do I map a custom token to the Polygon PoS bridge?
- What happens if my bridge transaction gets stuck?
- How do I check the status of a bridge transaction?

### RPC & Data
- What is the best free RPC endpoint for Polygon PoS?
- What RPC endpoint should I use for Polygon CDK chains?
- How do I use Alchemy's enhanced APIs on Polygon?
- How do I get all transactions for a wallet address on Polygon?
- How do I use `eth_getLogs` to filter events on Polygon?
- What is the difference between `eth_getTransactionByHash` and `eth_getTransactionReceipt`?
- How do I subscribe to new blocks on Polygon using WebSockets?
- Does the public Polygon RPC support `eth_subscribe`?
- How do I use The Graph on Polygon to index contract events?
- What indexing solutions are available for Polygon beyond The Graph?
- How do I read historical on-chain data without an archive node?

### Tokens & Standards
- What is the difference between MATIC and POL?
- Has MATIC been replaced by POL?
- What is the POL token contract address on Ethereum?
- What is the POL token contract address on Polygon PoS?
- How do I wrap/unwrap WMATIC on Polygon?
- Does Polygon support ERC-1155 tokens?
- How do I deploy an ERC-721 NFT on Polygon?
- What is the cost of minting an NFT on Polygon vs Ethereum?

### Tooling & SDKs
- Is there an official Polygon SDK?
- What is the Polygon CDK?
- How do I use the Polygon ID SDK?
- What Web3 libraries work best with Polygon — ethers.js, viem, or web3.js?
- Does Thirdweb support Polygon?
- How do I use OpenZeppelin contracts on Polygon?
- What wallets support Polygon PoS and CDK?

---

## 3. Validators

Stakers and validators securing the Polygon PoS network via the Heimdall + Bor consensus mechanism.

### Becoming a Validator
- How do I become a validator on Polygon PoS?
- What is the minimum stake required to become a validator on Polygon?
- How many validator slots are there on Polygon PoS?
- Is the validator set currently open or are all slots taken?
- How do I stake POL/MATIC to become a validator?
- What is the difference between a validator and a delegator on Polygon?
- How do I set up a validator node vs a regular full node?
- What is Heimdall's role in Polygon PoS validation?
- What is Bor's role in Polygon PoS validation?

### Staking & Rewards
- How are validator rewards calculated on Polygon PoS?
- What is the current staking APY for Polygon validators?
- How often are staking rewards distributed?
- What is the commission rate for validators?
- How do I change my commission rate?
- How do I claim staking rewards?
- What is the unbonding period for validators?
- What happens to my stake if I miss blocks?

### Slashing & Penalties
- What actions can get a validator slashed on Polygon?
- What is the slashing penalty for double signing?
- Has slashing been activated on Polygon PoS mainnet?
- How do I check if my validator has been slashed?
- How do I recover from a slashing event?

### Checkpointing
- What is a checkpoint on Polygon PoS?
- How often are checkpoints submitted to Ethereum?
- Who submits checkpoints and how are they selected?
- What happens if a checkpoint is delayed?
- How do I check the latest checkpoint on Ethereum?

### Monitoring & Operations
- How do I monitor my validator's uptime and performance?
- What metrics should I track for a healthy validator?
- What is the `heimdall-cli` command to check validator status?
- How do I check my validator's signing rate?
- How do I update my validator's signer address?
- What should I do if my validator is jailed?
- How do I unjail my validator?
- What is the difference between active and inactive validators?

### Governance
- How does governance work on Polygon PoS?
- How do validators vote on governance proposals?
- Where can I find active governance proposals for Polygon?
- What is the Polygon Improvement Proposal (PIP) process?
- How do I submit a governance proposal?

---

## 4. RPC Providers

Infrastructure providers serving JSON-RPC endpoints to dApps and users.

### Architecture & Infrastructure
- What is the expected throughput (requests/sec) of the Polygon PoS RPC?
- What hardware is recommended for a high-availability Polygon RPC node?
- How do I load balance across multiple Polygon nodes?
- What is the recommended setup for a highly available RPC endpoint?
- Should I run Bor or Erigon for an RPC node?
- What are the trade-offs between Bor and Erigon for RPC workloads?
- How do I configure Erigon for read-heavy RPC traffic?
- Does Polygon PoS support `eth_subscribe` at scale?
- How do I handle WebSocket connections at scale on Polygon?
- What is the best caching strategy for Polygon RPC responses?
- How do I serve `eth_getLogs` efficiently without overwhelming my node?

### Capacity & Rate Limiting
- What RPC methods are the most resource-intensive on Polygon?
- How do I rate limit users of my RPC endpoint?
- How do I detect and block abusive RPC clients?
- What is a reasonable default rate limit per API key?
- How do I handle burst traffic on my RPC infrastructure?
- What response caching can I safely apply to Polygon RPC calls?
- Which RPC methods are safe to cache and for how long?

### Reliability & Failover
- How do I implement failover between multiple Polygon nodes?
- How do I detect when a node falls behind and route traffic away from it?
- What is the maximum acceptable block lag for a production RPC?
- How do I monitor RPC latency and availability?
- What alerting should I set up for my Polygon RPC infrastructure?
- How do I handle a node crash without dropping client requests?

### Data & Compatibility
- Which Polygon RPC methods require an archive node?
- Does Polygon PoS support `debug_traceTransaction`?
- Does Polygon PoS support `trace_*` methods (OpenEthereum/Parity trace API)?
- How do I enable `debug` and `trace` namespaces on Bor?
- Do `eth_getProof` and state proofs work on Polygon PoS?
- How do I handle the Polygon PoS-specific `bor_*` RPC namespace?
- What is the `bor_getSigners` method?
- How do I serve EIP-1898 block parameter support correctly?
- Are there any Polygon-specific deviations from the Ethereum JSON-RPC spec?
- Does Polygon PoS return the same `eth_chainId` response as the network chain ID?

### Client Support & Upgrades
- How do I upgrade my Bor node with zero downtime?
- How do I coordinate Bor upgrades across a cluster of nodes?
- How do I test a new Bor version before rolling it to production?
- What is the process for a hard fork upgrade on Polygon PoS?
- How do I get notified of upcoming Polygon hard forks or breaking changes?
- What is the release cadence for Bor and Heimdall?
- How do I check which Bor version my nodes are running?

### Performance Tuning
- How do I tune Bor's `--cache` settings for RPC workloads?
- What database backend does Bor use and how do I optimize it?
- How do I reduce Bor's disk I/O under heavy `eth_getLogs` queries?
- What is the `--txpool.pricelimit` flag and when should I adjust it?
- How do I reduce response latency for `eth_getBlockByNumber`?
- What is the impact of enabling the `personal` namespace on a public RPC?

---

## Cross-Persona Questions (Commonly Asked by Multiple Groups)

### Gas & Fees
- What is the current base fee on Polygon PoS?
- How does EIP-1559 work on Polygon?
- What is a good `maxPriorityFeePerGas` to use right now?
- Why did my transaction get stuck with a low gas price?
- How do I speed up a stuck transaction on Polygon?
- How do I cancel a pending transaction on Polygon?
- What is the minimum gas price on Polygon?

### Network Status
- Is Polygon PoS mainnet experiencing any issues right now?
- What is the current block height on Polygon PoS?
- What is the finality time on Polygon PoS?
- What is the finality time on Polygon CDK chains?
- How many transactions per second can Polygon PoS handle?
- Where can I find real-time Polygon network stats?

### MATIC / POL Migration
- What is the MATIC to POL migration?
- Do I need to do anything to convert my MATIC to POL?
- What is the POL token contract address?
- Is MATIC still accepted for gas on Polygon PoS?
- What is the timeline for the MATIC → POL transition?
- Will MATIC stop working on Polygon?

### Security & Audits
- Has Polygon PoS been audited?
- Has Polygon CDK been audited?
- Where can I find Polygon's security audit reports?
- What should I do if I find a vulnerability in Polygon?
- Does Polygon have a bug bounty program?

---

*Last updated: April 2026*
*This document is intended as a living reference — add new questions as they surface from real users.*