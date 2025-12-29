"""Script to convert Hugging Face translation models to CTranslate2 format."""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def convert_model(
    model_name: str,
    output_dir: str,
    quantization: str = "int8"
):
    """
    Convert a Hugging Face model to CTranslate2 format.
    
    Args:
        model_name: Hugging Face model identifier (e.g., "Helsinki-NLP/opus-mt-en-es")
        output_dir: Directory to save the converted model
        quantization: Quantization type (int8, int16, float16, float32)
    """
    try:
        import ctranslate2
    except ImportError:
        logger.error(
            "ctranslate2 not installed. Install with:\n"
            "  pip install ctranslate2 transformers sentencepiece"
        )
        sys.exit(1)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Converting model: {model_name}")
    logger.info(f"Output directory: {output_path}")
    logger.info(f"Quantization: {quantization}")
    
    try:
        # Convert the model
        converter = ctranslate2.converters.TransformersConverter(model_name)
        converter.convert(
            output_dir=str(output_path),
            quantization=quantization,
            force=True
        )
        
        logger.info(f"✓ Model successfully converted to {output_path}")
        logger.info(f"✓ Model size: {get_dir_size(output_path):.2f} MB")
        
        # Verify the conversion
        logger.info("Verifying model...")
        translator = ctranslate2.Translator(str(output_path), device="cpu")
        logger.info(f"✓ Model loaded successfully")
        logger.info(f"  Device: {translator.device}")
        logger.info(f"  Compute type: {translator.compute_type}")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Conversion failed: {e}")
        return False


def get_dir_size(path: Path) -> float:
    """Get directory size in MB."""
    total = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    return total / (1024 * 1024)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Hugging Face models to CTranslate2 format"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Helsinki-NLP/opus-mt-en-es",
        help="Hugging Face model name (default: Helsinki-NLP/opus-mt-en-es)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/opus-mt-en-es-ct2",
        help="Output directory (default: models/opus-mt-en-es-ct2)"
    )
    parser.add_argument(
        "--quantization",
        type=str,
        choices=["int8", "int16", "float16", "float32"],
        default="int8",
        help="Quantization type (default: int8 for best speed/size)"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("CTranslate2 Model Conversion Tool")
    logger.info("=" * 60)
    
    success = convert_model(
        model_name=args.model,
        output_dir=args.output,
        quantization=args.quantization
    )
    
    if success:
        logger.info("=" * 60)
        logger.info("Conversion completed successfully!")
        logger.info(f"You can now use this model by setting:")
        logger.info(f"  CTRANSLATE2_MODEL_PATH={args.output}")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("Conversion failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

