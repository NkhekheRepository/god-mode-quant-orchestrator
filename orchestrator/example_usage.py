#!/usr/bin/env python3
"""
Example of how to use the Orchestrator Lifecycle Manager.
This demonstrates how to integrate the orchestrator package into main.py.
"""

import asyncio
import sys
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_orchestrator():
    """Run the orchestrator with lifecycle management"""
    try:
        # Import orchestrator package
        from orchestrator.config import OrchestratorConfig
        from orchestrator.lifecycle import OrchestratorLifecycle
        
        logger.info("Initializing Orchestrator Configuration...")
        
        # Load configuration from environment
        config = OrchestratorConfig.from_env()
        
        # Validate configuration
        warnings = config.validate()
        if warnings:
            logger.warning(f"Configuration warnings: {warnings}")
        
        # Log configuration summary
        config_dict = config.to_dict()
        logger.info(f"Configuration loaded: {config_dict}")
        
        # Create lifecycle manager
        logger.info("Creating Orchestrator Lifecycle Manager...")
        lifecycle = OrchestratorLifecycle(config)
        
        # Register custom handlers (optional)
        def on_startup_complete():
            logger.info("Custom startup handler: Orchestrator is ready!")
        
        def on_shutdown_start():
            logger.info("Custom shutdown handler: Cleaning up resources...")
        
        lifecycle.register_startup_handler(on_startup_complete)
        lifecycle.register_shutdown_handler(on_shutdown_start)
        
        # Start all components
        logger.info("Starting orchestrator components...")
        startup_success = await lifecycle.start()
        
        if not startup_success:
            logger.error("Failed to start orchestrator components")
            return 1
        
        logger.info("Orchestrator started successfully!")
        
        # Main loop - keep running until shutdown
        logger.info("Entering main loop. Press Ctrl+C to stop.")
        
        try:
            # Wait for shutdown signal
            await lifecycle._shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        # Graceful shutdown
        logger.info("Initiating graceful shutdown...")
        await lifecycle.stop()
        
        logger.info("Orchestrator shutdown complete")
        return 0
        
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}", exc_info=True)
        return 1


async def run_with_health_check():
    """
    Run orchestrator with health check endpoint.
    This example shows how to integrate with the existing Flask health server.
    """
    try:
        from orchestrator.config import OrchestratorConfig
        from orchestrator.lifecycle import OrchestratorLifecycle
        from flask import Flask, jsonify
        from threading import Thread
        
        # Load config
        config = OrchestratorConfig.from_env()
        
        # Create lifecycle manager
        lifecycle = OrchestratorLifecycle(config)
        
        # Create Flask app for health checks (if not using the built-in one)
        app = Flask(__name__)
        
        @app.route('/health')
        def health():
            return jsonify(lifecycle.health_check())
        
        @app.route('/health/ready')
        def ready():
            return jsonify({"status": "ready"}), 200
        
        @app.route('/health/live')
        def live():
            return jsonify({"status": "alive"}), 200
        
        # Start health server in background
        def run_health_server():
            app.run(host='0.0.0.0', port=config.api.health_port, debug=False, use_reloader=False)
        
        health_thread = Thread(target=run_health_server, daemon=True)
        health_thread.start()
        
        logger.info(f"Health server started on port {config.api.health_port}")
        
        # Start orchestrator
        await lifecycle.start()
        
        # Run until shutdown
        await lifecycle._shutdown_event.wait()
        
        # Shutdown
        await lifecycle.stop()
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to run orchestrator: {e}", exc_info=True)
        return 1


async def demo_component_management():
    """
    Demonstrate component management features.
    """
    from orchestrator.config import OrchestratorConfig
    from orchestrator.lifecycle import OrchestratorLifecycle, ComponentState
    
    config = OrchestratorConfig.from_env()
    lifecycle = OrchestratorLifecycle(config)
    
    # Register custom components
    lifecycle._register_component("custom_service", {"type": "demo"})
    
    # Update component state
    lifecycle._update_component_state("custom_service", ComponentState.RUNNING)
    
    # Get component status
    component = lifecycle.get_component_status("custom_service")
    if component:
        print(f"Component '{component.name}' state: {component.state.value}")
        print(f"Component metadata: {component.metadata}")
    
    # Health check
    health = lifecycle.health_check()
    print(f"Overall health: {health['status']}")
    print(f"Components: {list(health['components'].keys())}")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "demo":
            print("Running component management demo...")
            asyncio.run(demo_component_management())
            return 0
        elif command == "health":
            print("Running with health check server...")
            return asyncio.run(run_with_health_check())
    
    # Default: run full orchestrator
    return asyncio.run(run_orchestrator())


if __name__ == "__main__":
    sys.exit(main())