from PIL import Image
import pytesseract

# Path to the image file
image_path = './docs/profile.pdf'

# Open the image using Pillow
img = Image.open(image_path)

# Use pytesseract to extract text
text = pytesseract.image_to_string(img)

# Print the extracted text
print(text)