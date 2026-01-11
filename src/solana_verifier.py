import logging
import time
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solders.signature import Signature
from .config import SOLANA_RPC_URL

logger = logging.getLogger(__name__)

class SolanaVerifier:
    def __init__(self):
        self.client = AsyncClient(SOLANA_RPC_URL)

    async def verify_transaction(self, signature_str: str, expected_sender: str, expected_amount: float) -> bool:
        """
        Verifies a self-transfer transaction.
        """
        try:
            signature = Signature.from_string(signature_str)
            # Fetch transaction with jsonParsed encoding to easily read instructions
            resp = await self.client.get_transaction(signature, max_supported_transaction_version=0)
            
            if resp.value is None:
                logger.warning(f"Transaction {signature_str} not found on chain.")
                return False

            tx = resp.value
            
            # 1. Verify it is a successful transaction
            if tx.meta.err is not None:
                logger.warning(f"Transaction {signature_str} failed on chain.")
                return False

            # 2. Extract transaction details
            # We need to manually parse the message if we are not using jsonParsed or if it comes back as a different format.
            # Using get_transaction usually returns verified data. 
            # For simplicity in this check, we look at the pre/post balances or parse the instruction.
            # A self-transfer is easiest verified by checking the sender account in the account keys and checking the instruction data.
            # However, looking at pre/post balances is safer and easier for amounts.
            
            # Find the index of the sender
            account_keys = tx.transaction.message.account_keys
            sender_pubkey_obj = Pubkey.from_string(expected_sender)
            
            sender_index = -1
            for idx, key in enumerate(account_keys):
                if key == sender_pubkey_obj:
                    sender_index = idx
                    break
            
            if sender_index == -1:
                logger.warning(f"Sender {expected_sender} not found in transaction keys.")
                return False

            # Check pre and post balances
            # Note: This is a simplifiction. If gas fees are involved (which they are), exact equality on sender balance change is hard directly.
            # BUT, the self-transfer means:
            # Sender Balance Change = - (Amount + Fee)
            # Receiver Balance Change (which is sender) ... wait.
            # If I send to myself:
            # Initial: 100.
            # Send 1. Fee 0.000005.
            # Final: 98.999995.
            # Change: -0.000005. The 1 SOL didn't leave the account, it just looped.
            # So looking at balance changes for self-transfer is tricky because the amount cancels out.
            
            # ALTERNATIVE: Parse the instruction.
            # We look for a System Program Transfer instruction where source == dest == expected_sender
            # and lamports == expected_amount * 1e9
            
            instructions = tx.transaction.message.instructions
            found_transfer = False
            expected_lamports = int(expected_amount * 1_000_000_000)
            
            # We need to know the index of SystemProgram? 
            # Or just iterate and decode.
            # Since parsing raw instructions can be complex without the layout, 
            # we rely on the implementation details of System Program Transfer.
            
            # Ideally we'd use `get_transaction(..., encoding="jsonParsed")` but `solana-py` async client typing is sometimes tricky.
            # Let's try to fetch with jsonParsed if possible or use the parsed result if available.
            
            # START RE-FETCH WITH JSON PARSED FOR EASIER LOGIC
            # Note: The `solders` client might return objects that are hard to iterate if not strictly typed.
            # We will use the raw RPC call via the client to ensure we get a dict we can parse easily.
            
            # Actually, `get_transaction` allows encoding.
            # But let's assume standard object return.
            
            # Let's trust the balances if we can.
            # Wait, if I transfer 1 SOL to myself, my balance decreases ONLY by the fee.
            # So verification by balance change is IMPOSSIBLE for self-transfer.
            # WE MUST PARSE THE INSTRUCTION.
            
            # Parsing Instruction:
            # System Program ID: 11111111111111111111111111111111
            # Instruction Index: 2 (Transfer)
            # Data: [2, 0, 0, 0, amount_low, ..., amount_high] (little endian lamports)
            
            for instr in instructions:
                # Check program ID
                program_id_index = instr.program_id_index
                program_id = account_keys[program_id_index]
                
                if str(program_id) == "11111111111111111111111111111111": # System Program
                    data = instr.data
                    # Instruction index for Transfer is 2. 
                    # Data layout: [instruction_type (4 bytes), lamports (8 bytes)]
                    if len(data) >= 12:
                         type_idx = int.from_bytes(data[0:4], "little")
                         if type_idx == 2: # Transfer
                             lamports = int.from_bytes(data[4:12], "little")
                             
                             # Check indices
                             # Accounts: [source, destination]
                             if len(instr.accounts) >= 2:
                                 src_idx = instr.accounts[0]
                                 dest_idx = instr.accounts[1]
                                 
                                 src_key = str(account_keys[src_idx])
                                 dest_key = str(account_keys[dest_idx])
                                 
                                 if src_key == expected_sender and dest_key == expected_sender:
                                     # Found self transfer!
                                     # Allow small float error or exact match? Lamports are integers.
                                     # expected_amount is float SOL.
                                     # We need to be careful with precision. 
                                     # Better: we allow a tiny delta or expected_lamports match.
                                     
                                     if abs(lamports - expected_lamports) < 10: # Allow tiny rounding error if any
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
