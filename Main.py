import os
import json
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

# Define states for the conversation
CLIENT_NAME, DESCRIPTION, START_DATETIME, END_DATETIME, LOCATION, TEAM_MEMBERS = range(6)

# Load existing appointments
APPOINTMENTS_FILE = "appointments.json"
if not os.path.exists(APPOINTMENTS_FILE):
    with open(APPOINTMENTS_FILE, "w") as f:
        json.dump([], f)

# Setup logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome to the Appointment Bot! Use /add_appointment to create a new appointment.")

async def add_appointment(update: Update, context: CallbackContext):
    await update.message.reply_text("Enter client name:")
    return CLIENT_NAME

async def collect_client_name(update: Update, context: CallbackContext):
    context.user_data["client_name"] = update.message.text
    await update.message.reply_text("Enter appointment description:")
    return DESCRIPTION

async def collect_description(update: Update, context: CallbackContext):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("Enter start date and time (YYYY-MM-DD HH:MM):")
    return START_DATETIME

async def collect_start_datetime(update: Update, context: CallbackContext):
    context.user_data["start_datetime"] = update.message.text
    await update.message.reply_text("Enter end date and time (YYYY-MM-DD HH:MM):")
    return END_DATETIME

async def collect_end_datetime(update: Update, context: CallbackContext):
    context.user_data["end_datetime"] = update.message.text
    await update.message.reply_text("Enter location link or address:")
    return LOCATION

async def collect_location(update: Update, context: CallbackContext):
    context.user_data["location"] = update.message.text
    await update.message.reply_text("Enter team member usernames separated by commas:")
    return TEAM_MEMBERS

async def collect_team_members(update: Update, context: CallbackContext):
    team_members = update.message.text.split(",")
    team_members = [member.strip() for member in team_members]
    context.user_data["team_members"] = team_members

    # Save appointment
    new_appointment = {
        "client_name": context.user_data["client_name"],
        "description": context.user_data["description"],
        "start_datetime": context.user_data["start_datetime"],
        "end_datetime": context.user_data["end_datetime"],
        "location": context.user_data["location"],
        "team_members": team_members
    }
    
    with open(APPOINTMENTS_FILE, "r+") as f:
        appointments = json.load(f)
        appointments.append(new_appointment)
        f.seek(0)
        json.dump(appointments, f, indent=4)
    
    message = (f"📅 *New Appointment Created!*"
               f"👤 Client: {new_appointment['client_name']}\n"
               f"📄 Description: {new_appointment['description']}\n"
               f"🕒 Start: {new_appointment['start_datetime']}\n"
               f"🕒 End: {new_appointment['end_datetime']}\n"
               f"📍 Location: {new_appointment['location']}\n"
               f"👥 Team Members: {', '.join(new_appointment['team_members'])}")
    
    # Send message to group
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=message, parse_mode="Markdown")
    
    # Send message to each team member (direct message)
    for member in team_members:
        try:
            await bot.send_message(chat_id=member, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Could not send message to {member}: {e}")
    
    await update.message.reply_text("Appointment added successfully!")
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# Main function
def main():
    app = Application.builder().token(TOKEN).build()
    
    appointment_handler = ConversationHandler(
        entry_points=[CommandHandler("add_appointment", add_appointment)],
        states={
            CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_client_name)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_description)],
            START_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_start_datetime)],
            END_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_end_datetime)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_location)],
            TEAM_MEMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_team_members)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(appointment_handler)
    
    app.run_polling()

if __name__ == "__main__":
    main()
