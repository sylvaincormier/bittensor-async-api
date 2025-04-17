#!/usr/bin/env python3
import os
import sys
import logging
import traceback
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bittensor_test")

def test_bittensor_operations():
    """Test Bittensor operations needed for the application."""
    try:
        logger.info("Testing Bittensor operations...")
        
        # Import libraries
        logger.info("Importing Bittensor...")
        import bittensor
        logger.info(f"Bittensor imported successfully, version: {bittensor.__version__}")
        
        # Create wallet
        logger.info("Creating wallet...")
        wallet = bittensor.wallet()
        logger.info(f"Wallet created: {wallet}")
        
        # Set up parameters
        netuid = int(os.getenv("NETUID", "18"))
        hotkey = os.getenv("WALLET_HOTKEY", "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v")
        logger.info(f"Using netuid: {netuid}, hotkey: {hotkey}")
        
        # Create subtensor connection
        logger.info("Creating subtensor connection to testnet...")
        start_time = time.time()
        
        try:
            subtensor = bittensor.subtensor(network="test")
            elapsed = time.time() - start_time
            logger.info(f"Connected to subtensor after {elapsed:.2f} seconds")
            
            # Check connection by getting block number
            logger.info("Getting current block...")
            block = subtensor.get_current_block()
            logger.info(f"Current block: {block}")
            
            # Try to get tao dividends for the subnet
            logger.info(f"Attempting to get dividends for netuid {netuid}...")
            
            # Try different methods that might exist
            try:
                # Try the main method we need for the application
                logger.info("Trying get_tao_dividends_for_subnet method...")
                dividends = subtensor.get_tao_dividends_for_subnet(netuid=netuid)
                logger.info(f"Tao dividends for subnet {netuid}: {dividends}")
            except Exception as e:
                logger.warning(f"get_tao_dividends_for_subnet failed: {e}")
                
                # Try alternate methods
                try:
                    logger.info("Trying get_dividends method...")
                    dividends = subtensor.get_dividends(netuid=netuid)
                    logger.info(f"Dividends for subnet {netuid}: {dividends}")
                except Exception as e:
                    logger.warning(f"get_dividends failed: {e}")
                    
                    # One more attempt
                    try:
                        logger.info("Trying neurons method to get subnet data...")
                        neurons = subtensor.neurons(netuid=netuid)
                        logger.info(f"Found {len(neurons)} neurons on subnet {netuid}")
                    except Exception as e:
                        logger.error(f"neurons method failed: {e}")
                        return False
            
            # Test async connection if it exists
            try:
                logger.info("Testing AsyncSubtensor if available...")
                async_subtensor = bittensor.AsyncSubtensor(network="test")
                logger.info("AsyncSubtensor created successfully")
            except Exception as e:
                logger.warning(f"AsyncSubtensor not available: {e}")
            
            return True
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error after {elapsed:.2f} seconds: {e}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting Bittensor operations test...")
    result = test_bittensor_operations()
    
    if result:
        logger.info("✅ Test successful! Bittensor operations working.")
        sys.exit(0)
    else:
        logger.error("❌ Test failed! There are issues with Bittensor operations.")
        sys.exit(1)