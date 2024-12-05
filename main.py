import logging
from io import BytesIO
from bakong_khqr import KHQR
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
import qrcode
from qrcode.constants import ERROR_CORRECT_L
import time
import asyncio
from keep_alive import keep_alive

keep_alive()
# Set up the logging module to debug the bot
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the Bakong Developer Token and create an instance of KHQR
BAKONG_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTFhNzgzZmQwOWE5NGQxIn0sImlhdCI6MTczMDM4Nzc1MSwiZXhwIjoxNzM4MTYzNzUxfQ.jSBGdjXNmznbcc5wXO5J-PEevLfraJIIESMODAJvjyo'  # Replace with your Bakong token
khqr = KHQR(BAKONG_TOKEN)

# Define the group ID to send all messages to
GROUP_ID = -1002302838310  # Replace with your actual group ID

# Conversation states
SERVICE, AMOUNT, LINK = range(3)

# Dummy product catalog for the SMM services
PRODUCTS = {
    "Facebook Page Like": 1.47,  # $1 for 1000 likes
    "Facebook Page Follower": 1.68,  # $2 for 1000 followers
    "Facebook Page (Best) Like + Follow" : 2.46,
    "Facebook Account Follow": 1.68,
    "Tiktok Like": 0.97,  # $1 for 1000 likes
    "Tiktok Follower": 2.1,  # $2 for 1000 followers
    "Tiktok View": 0.08
    
}

# Function to send a message to the group
async def send_to_group(application, message):
    try:
        # Send the message to the specified group
        await application.bot.send_message(chat_id=GROUP_ID, text=message)
    except Exception as e:
        logger.error(f"Failed to send message to group: {e}")

# Function to start the bot and show available services
async def start(update: Update, context: CallbackContext):
    # Create a 2-column keyboard
    keyboard = []
    services = list(PRODUCTS.keys())  # List of available services
    
    # Loop through the services and create pairs of buttons
    for i in range(0, len(services), 2):
        keyboard.append([KeyboardButton(services[i]), KeyboardButton(services[i+1] if i+1 < len(services) else "")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
    f"🎉 Welcome to the SMM Bot! {update.message.from_user.full_name} \n\n"
    f"Facebook Page Likes: ${PRODUCTS['Facebook Page Like']} per 1000 likes\n"
    "────────────────────\n"
    f"Facebook Page Followers: ${PRODUCTS['Facebook Page Follower']} per 1000 followers\n"
    "────────────────────\n"
    f"Facebook Page (Best) Like + Follow: ${PRODUCTS['Facebook Page (Best) Like + Follow']} per 1000\n"
    "────────────────────\n"
    f"Facebook Account Follows: ${PRODUCTS['Facebook Account Follow']} per 1000 follows\n"
    "────────────────────\n"
    f"TikTok Likes: ${PRODUCTS['Tiktok Like']} per 1000 likes\n"
    "────────────────────\n"
    f"TikTok Followers: ${PRODUCTS['Tiktok Follower']} per 1000 followers\n"
    "────────────────────\n"
    f"TikTok Views: ${PRODUCTS['Tiktok View']} per 1000 views\n\n"
    "✨ តម្លៃនឹងមានការផ្លាស់ប្តូជានិច្ច កប់សេរី 🚀",
    reply_markup=reply_markup
)


    # Send a message to the group every time a user starts the bot
    await send_to_group(context.application, f"New user started the bot: {update.message.from_user.full_name} (@{update.message.from_user.username})")

# Function to handle service selection
async def handle_service(update: Update, context: CallbackContext):
    service_name = update.message.text
    if service_name in PRODUCTS:
        context.user_data["service"] = service_name  # Store the selected service
        await update.message.reply_text(f"You selected {service_name}. Please input the amount and social link in the format [Amount Link] \nExample : 1000 Yourlink.")
        return AMOUNT
    elif service_name == "Check Balance":
        balance = context.user_data.get("balance", 0)
        await update.message.reply_text(f"Your current balance is: ${balance:.2f}")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Invalid selection. Please choose a valid service.")
        return ConversationHandler.END

# Function to handle amount and social link input
async def handle_amount_and_link(update: Update, context: CallbackContext):
    try:
        # Split the user's message into amount and link
        user_input = update.message.text.strip().split()
        
        if len(user_input) != 2:
            await update.message.reply_text("Please provide both amount and social link in the format: 'amount social_link'")
            return

        amount = float(user_input[0])
        social_link = user_input[1]

        # Check if the amount meets the minimum order requirement (1000 units)
        if amount < 1000:
            await update.message.reply_text("The minimum order quantity is 1000. Please enter a larger amount.")
            return

        # Validate the social link (optional, could be more robust)
        if "facebook" in social_link or "instagram" in social_link or "youtube" in social_link or "tiktok" in social_link:
            service_name = context.user_data["service"]
            product_price = PRODUCTS[service_name]

            # Calculate total amount (e.g., $5 per 1000 likes)
            total_amount = amount * product_price / 1000  # product_price is now the amount for 1000 units

            # Store the amount for later use in group message
            context.user_data["amount"] = int(amount)  # Store amount as integer (e.g., 100)

            # Generate the payment QR code using Bakong
            qr_data = khqr.create_qr(
                bank_account="lyhang_hyper@aclb",  # Replace with your bank account
                merchant_name="Hanji Zoe",
                merchant_city="Phnom Penh",
                amount=total_amount,
                currency="USD",
                store_label="Hanji SMM",
                phone_number="90854415",
                bill_number="TRX126786182",  # Transaction ID
                terminal_label="SMM-01",
                static=False
            )

            md5_hash = khqr.generate_md5(qr_data)

            # Generate the QR code image
            qr = qrcode.QRCode(
                version=1,
                error_correction=ERROR_CORRECT_L,
                box_size=10,
                border=1
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")

            # Save the image to a BytesIO object
            byte_io = BytesIO()
            qr_img.save(byte_io, 'PNG')
            byte_io.seek(0)

            # Send the QR code to the user
            await update.message.reply_photo(
                photo=byte_io,
                caption=f"Please scan this QR code to make the payment of ${total_amount:.2f} for {int(amount)} {service_name}.\n"
                f"Link: {social_link}\n\n"
                "Note: កូដ QR នេះនឹងផុតកំណត់ក្នុងរយៈពេល1នាទី។ សូមបញ្ចូលការទូទាត់របស់អ្នកក្នុងរយៈពេលនេះ។\n"
                "នៅពេលដែលអ្នកស្កេនរួចរាល់ និងបង់ប្រាក់រួចរាល់ ហើយអ្នកអាចធ្វើការកម្មង់ទិញមួយទៀតបាន។"
            )

            # Send message to the group about the transaction
            await send_to_group(context.application, f"Payment QR sent to {update.message.from_user.full_name} ({update.message.from_user.id}) for {service_name}.")

            # Start checking the payment status after a short delay
            await check_payment(update, context, md5_hash, total_amount)
        else:
            await update.message.reply_text("The social link provided is not valid. Please make sure it's a valid Facebook, Instagram, or YouTube link.")
            return

    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a valid number.")
        return ConversationHandler.END

# Function to check the payment status
async def check_payment(update: Update, context: CallbackContext, md5_hash: str, amount: float):
    max_attempts = 12  # 12 attempts (5 seconds interval for 1 minute)
    for attempt in range(max_attempts):
        try:
            # Check payment status using KHQR
            payment_status = khqr.check_payment(md5_hash)

            if payment_status == "PAID":
                # Update user's balance
                user_id = update.message.from_user.id
                current_balance = context.user_data.get("balance", 0)
                new_balance = current_balance + amount
                context.user_data["balance"] = new_balance

                # Get the social link and service name
                service_name = context.user_data["service"]
                social_link = update.message.text.split()[1]  # Assuming the link was the second part of the message

                # Preserve the original quantity (amount)
                original_amount = context.user_data.get("amount", 0)

                # Notify user of the success
                await update.message.reply_text(
                    f"✅ Payment confirmed! "
                    f"Thank you for purchasing {original_amount} {context.user_data['service']}!\n"
                    f"Please wait while we process your order."
                )

                # Send formatted message to the group
                group_message = (f"🚨 Order Alert 🚨\n"
                 f"📱 From: @{update.message.from_user.username} ({user_id})\n"
                 f"🛒 Order: {original_amount} of {service_name}\n"
                 f"💰 Price: ${new_balance:.2f}\n"
                 f"🔗 Link: {social_link}")
                await send_to_group(context.application, group_message)
                return  # Exit if payment is confirmed

        except Exception as e:
            logger.error(f"Error checking payment: {e}")
            await update.message.reply_text(f"An error occurred while checking the payment status: {e}")

        # Wait for 5 seconds before checking again
        await asyncio.sleep(5)

    # If the loop completes and the payment is not confirmed
    await update.message.reply_text("❌ Payment expired! Please try again.")

# Function to handle errors
def error(update: Update, context: CallbackContext):
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    # Set up the Application with your bot's API token
    application = Application.builder().token("7810436817:AAFVRbCjY7-lbEGy2nqTNQmyR9J4rsoAmTc").build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("|".join(PRODUCTS.keys())), handle_service))  # Service selection handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount_and_link))  # Amount and link handler

    # Register error handler
    application.add_error_handler(error)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
