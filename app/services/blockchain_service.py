"""
Blockchain service for interacting with EscrowManager smart contract.
This service releases milestone funds based on building registry validation.
"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_account.signers.local import LocalAccount

logger = logging.getLogger(__name__)


class BlockchainService:
    """
    Service to interact with the EscrowManager smart contract.
    Releases milestone funds based on building registry validation.
    """
    
    @staticmethod
    def load_abi(abi_file_path: str) -> List[Dict[str, Any]]:
        """
        Load contract ABI from a JSON file.
        
        Args:
            abi_file_path: Path to the ABI JSON file
            
        Returns:
            List of ABI definitions
            
        Raises:
            FileNotFoundError: If ABI file doesn't exist
            ValueError: If ABI file is invalid JSON
        """
        abi_path = Path(abi_file_path)
        
        if not abi_path.exists():
            raise FileNotFoundError(f"ABI file not found: {abi_file_path}")
        
        try:
            with open(abi_path, 'r') as f:
                abi = json.load(f)
            
            # Handle case where ABI is wrapped in an object with an "abi" key
            if isinstance(abi, dict) and "abi" in abi:
                abi = abi["abi"]
            
            if not isinstance(abi, list):
                raise ValueError("ABI must be a JSON array")
            
            logger.info(f"Successfully loaded ABI from {abi_file_path}")
            return abi
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in ABI file: {e}")
    
    def __init__(
        self,
        rpc_url: str,
        contract_address: str,
        abi_file_path: str,
        private_key: Optional[str] = None,
        chain_id: int = 1
    ):
        """
        Initialize the blockchain service.
        
        Args:
            rpc_url: Ethereum RPC endpoint URL
            contract_address: Address of the deployed EscrowManager contract
            abi_file_path: Path to the contract ABI JSON file
            private_key: Private key of the oracle account (optional for read-only operations)
            chain_id: Chain ID (1 for mainnet, 11155111 for Sepolia, etc.)
        """
        self.rpc_url = rpc_url
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.chain_id = chain_id
        
        abi = self.load_abi(abi_file_path)

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not self.w3.is_connected():
            raise RuntimeError(f"Failed to connect to Ethereum node at {rpc_url}")
        
        self.contract: Contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=abi
        )
        
        self.account: Optional[LocalAccount] = None
        if private_key:
            self.account = Account.from_key(private_key)
            logger.info(f"Blockchain service initialized with account: {self.account.address}")
        else:
            logger.warning("Blockchain service initialized without private key (read-only mode)")
    
    def release_milestone_funds(
        self,
        building_id: int,
        gas_limit: int = 300000
    ) -> Dict[str, Any]:
        """
        Release funds for the next milestone.
        The contract will release funds for the next unreleased milestone based on 
        the building registry's validation status.
        
        Args:
            building_id: The ID of the building
            gas_limit: Gas limit for the transaction
            
        Returns:
            Dictionary containing transaction hash and receipt
            
        Raises:
            RuntimeError: If private key is not configured or transaction fails
        """
        if not self.account:
            raise RuntimeError("Cannot release funds: private key not configured")
        
        try:
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            gas_price = self.w3.eth.gas_price
            
            transaction = self.contract.functions.releaseMilestoneFunds(
                building_id
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'from': self.account.address
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            logger.info(f"signed transaction info: {signed_txn}")
            
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"Funds release transaction sent: {tx_hash.hex()}")
            
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if tx_receipt['status'] == 0:
                raise RuntimeError(f"Transaction failed: {tx_hash.hex()}")
            
            logger.info(f"Funds released for building {building_id}")
            
            return {
                "transaction_hash": tx_hash.hex(),
                "block_number": tx_receipt['blockNumber'],
                "gas_used": tx_receipt['gasUsed'],
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to release funds: {str(e)}")
            raise RuntimeError(f"Failed to release funds on blockchain: {str(e)}")
    
    def get_escrow_info(self, building_id: int) -> Dict[str, Any]:
        """
        Get escrow information for a building.
        
        Args:
            building_id: The ID of the building
            
        Returns:
            Dictionary containing escrow information
            
        Raises:
            RuntimeError: If contract call fails
        """
        try:
            result = self.contract.functions.getEscrowInfo(building_id).call()
            
            return {
                "total_escrowed": result[0],
                "total_released": result[1],
                "last_released_milestone": result[2],
                "total_milestones": result[3],
                "developer": result[4]
            }
            
        except Exception as e:
            logger.error(f"Failed to get escrow info: {str(e)}")
            raise RuntimeError(f"Failed to get escrow info from blockchain: {str(e)}")
    
    def is_connected(self) -> bool:
        """Check if connected to the Ethereum network."""
        return self.w3.is_connected()
    
    def get_oracle_address(self) -> Optional[str]:
        """Get the account address."""
        return self.account.address if self.account else None
