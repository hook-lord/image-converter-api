from typing import Tuple
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, Response
from PIL import Image
from io import BytesIO
import logging

app = FastAPI()


async def resize_in_memory(
    image_data: bytes,
    max_width: int = 800,
    quality: int = 85,
    output_format: str = "WEBP",
) -> bytes:
    """
    Process an image entirely in memory

    Args:
        image_data: Raw bytes of the input image
        max_width: Maximum width to resize to
        quality: Output image quality (1-100)
        output_format: Output format (WEBP, JPEG, etc)

    Returns:
        Processed image as bytes
    """
    try:
        # Load image from bytes
        with Image.open(BytesIO(image_data)) as img:
            # Convert to RGB if needed
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.getchannel("A"))
                img = background

            # Calculate new dimensions maintaining aspect ratio
            aspect_ratio = img.size[1] / img.size[0]
            new_width = min(max_width, img.size[0])
            new_height = int(new_width * aspect_ratio)

            # Resize image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save to bytes
            output_buffer = BytesIO()
            resized_img.save(
                output_buffer, format=output_format, quality=quality, optimize=True
            )

            return output_buffer.getvalue()

    except Exception as e:
        logging.error(f"Image processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/resize")
async def resize_image(file: UploadFile, max_width: int = 800, quality: int = 85):
    """
    Endpoint to resize an image and convert to WebP
    """
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read file into memory
    contents = await file.read()

    # Process the image
    processed_image = await resize_in_memory(
        contents, max_width=max_width, quality=quality
    )

    # Return the processed image
    return Response(content=processed_image, media_type="image/webp")


@app.post("/crop-square")
async def crop_square(file: UploadFile, quality: int = 85):
    """
    Endpoint to crop an image to a square from the center
    """
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        contents = await file.read()

        # Load image from bytes
        with Image.open(BytesIO(contents)) as img:
            # Convert to RGB if needed
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.getchannel("A"))
                img = background

            # Calculate crop dimensions
            crop_size = min(img.size)
            left = (img.size[0] - crop_size) // 2
            top = (img.size[1] - crop_size) // 2
            right = left + crop_size
            bottom = top + crop_size

            # Crop image
            cropped = img.crop((left, top, right, bottom))

            # Save to bytes
            output_buffer = BytesIO()
            cropped.save(output_buffer, format="WEBP", quality=quality, optimize=True)

            return Response(content=output_buffer.getvalue(), media_type="image/webp")

    except Exception as e:
        logging.error(f"Image processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/crop")
async def crop(
    file: UploadFile, box: tuple[float, float, float, float], quality: int = 85
):
    """
    Endpoint that crops and image according to passed in coordinates in the order Left, top, right, bottom.
    """
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        contents = await file.read()

        with Image.open(BytesIO(contents)) as img:
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.getchannel("A"))
                img = background
            cropped = img.crop(box)
            output_buffer = BytesIO()
            cropped.save(output_buffer, format="WEBP", quality=quality, optimize=True)
    except Exception as exc:
        raise HTTPException(400, str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
