import logging
from solana.rpc.async_api import AsyncClient
from solders.signature import Signature
from .config import SOLANA_RPC_URL

logger = logging.getLogger(__name__)

class SolanaVerifier:
    def __init__(self):
        self.client = AsyncClient(SOLANA_RPC_URL)

    async def verify_transaction(self, signature_str: str, expected_sender: str, expected_amount: float) -> bool:
        """
        Verifies a self-transfer transaction using jsonParsed encoding.
        """
        try:
            signature = Signature.from_string(signature_str)
            # Fetch transaction with jsonParsed encoding to easily read instructions
            resp = await self.client.get_transaction(
                signature, 
                encoding="jsonParsed", 
                max_supported_transaction_version=0
            )
            
            if resp.value is None:
                logger.warning(f"Transaction {signature_str} not found on chain.")
                return False

            # Correct hierarchy for EncodedConfirmedTransactionWithStatusMeta
            inner_tx_with_meta = resp.value.transaction
            meta = inner_tx_with_meta.meta
            
            # 1. Verify it is a successful transaction
            if meta.err is not None:
                logger.warning(f"Transaction {signature_str} failed on chain: {meta.err}")
                return False

            # 2. Extract and verify instructions
            # For jsonParsed, instructions are found in:
            # resp.value.transaction.transaction.message.instructions
            actual_tx = inner_tx_with_meta.transaction
            instructions = actual_tx.message.instructions
            
            found_transfer = False
            expected_lamports = int(expected_amount * 1_000_000_000)
            
            from solders.transaction_status import ParsedInstruction
            
            for instr in instructions:
                # In jsonParsed, we check for ParsedInstruction
                if isinstance(instr, ParsedInstruction):
                    parsed_data = instr.parsed
                    if (
                        instr.program == "system" and 
                        parsed_data.get("type") == "transfer"
                    ):
                        info = parsed_data.get("info", {})
                        src_key = info.get("source")
                        dest_key = info.get("destination")
                        lamports = info.get("lamports")
                        
                        if (
                            src_key == expected_sender and 
                            dest_key == expected_sender and
                            abs(lamports - expected_lamports) < 10 # Allow tiny rounding error
                        ):
                            found_transfer = True
                            break

            if found_transfer:
                return True
            else:
                logger.warning("No matching self-transfer instruction found.")
                return False

        except Exception as e:
            logger.exception(f"Verification error: {e}")
            return False

    async def close(self):
        await self.client.close()
