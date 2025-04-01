import os
import json
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackContext, 
    ConversationHandler, CallbackQueryHandler, filters
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

# JSON file to store appointments
APPOINTMENTS_FILE = "appointments.json"

# Role-based Access
ADMINS = [1139205377, 987654321]  # Replace with real Telegram user IDs

# Appointment Conversation States
(
    CLIENT_NAME, DESCRIPTION, START_DATETIME, END_DATETIME, 
    LOCATION, SELECT_TEAM, CONFIRM_APPOINTMENT
) = range(7)

# Team Members List (Change as Needed)
TEAM_MEMBERS = {
    "John Doe": "123456789",
    "Jane Smith": "987654321",
    "Mike Lee": "654321987"
}

# Load Appointments
def load_appointments():
    try:
        with open(APPOINTMENTS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save Appointments
def save_appointments(appointments):
    with open(APPOINTMENTS_FILE, "w") as f:
        json.dump(appointments, f, indent=4)

# Start Booking Process
async def add_appointment(update: Update, context: CallbackContext) -> int:
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("❌ You are not authorized to add appointments.")
        return ConversationHandler.END

    await update.message.reply_text("📌 Enter the *Client Name*:")
    return CLIENT_NAME

# Collect Client Name
async def client_name(update: Update, context: CallbackContext) -> int:
    context.user_data["client_name"] = update.message.text
    await update.message.reply_text("📝 Enter the *Appointment Description*:")
    return DESCRIPTION

# Collect Description
async def description(update: Update, context: CallbackContext) -> int:
    context.user_data["description"] = update.message.text
    await update.message.reply_text("📅 Enter the *Start Date & Time* (e.g., 2025-04-01 10:00):")
    return START_DATETIME

# Collect Start Date & Time
async def start_datetime(update: Update, context: CallbackContext) -> int:
    context.user_data["start_datetime"] = update.message.text
    await update.message.reply_text("⌛ Enter the *End Date & Time* (e.g., 2025-04-01 12:00):")
    return END_DATETIME

# Collect End Date & Time
async def end_datetime(update: Update, context: CallbackContext) -> int:
    context.user_data["end_datetime"] = update.message.text
    await update.message.reply_text("📍 Send the *Google Maps Location Link*:")
    return LOCATION

# Collect Location
async def location(update: Update, context: CallbackContext) -> int:
    context.user_data["location"] = update.message.text

    # Generate Inline Keyboard for Team Member Selection
    keyboard = [
        [InlineKeyboardButton(name, callback_data=name)] for name in TEAM_MEMBERS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("👥 Select *Team Members* (Click on Names). Click /done when finished.", reply_markup=reply_markup)
    context.user_data["selected_team"] = []
    
    return SELECT_TEAM

# Handle Team Member Selection
async def select_team(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    member_name = query.data
    if member_name not in context.user_data["selected_team"]:
        context.user_data["selected_team"].append(member_name)

    # Update Selection Message
    selected_names = ", ".join(context.user_data["selected_team"])
    await query.edit_message_text(f"✅ Selected Team Members: {selected_names}\n\nClick more names or /done when finished.")

    return SELECT_TEAM

# Confirm and Save Appointment
async def confirm_appointment(update: Update, context: CallbackContext) -> int:
    appointments = load_appointments()
    appointment_id = str(len(appointments) + 1)

    appointments[appointment_id] = {
        "client_name": context.user_data["client_name"],
        "description": context.user_data["description"],
        "start_datetime": context.user_data["start_datetime"],
        "end_datetime": context.user_data["end_datetime"],
        "location": context.user_data["location"],
        "team": context.user_data["selected_team"]
    }

    save_appointments(appointments)

    # Generate Appointment Message
    appointment_details = (
        f"📌 *New Appointment Scheduled!*\n\n"
        f"👤 Client: {context.user_data['client_name']}\n"
        f"📝 Description: {context.user_data['description']}\n"
        f"📅 Start: {context.user_data['start_datetime']}\n"
        f"⌛ End: {context.user_data['end_datetime']}\n"
        f"📍 Location: {context.user_data['location']}\n"
        f"👥 Team: {', '.join(context.user_data['selected_team'])}\n"
    )

    await update.message.reply_text(f"✅ Appointment Confirmed!\n\n{appointment_details}")

    # Send to Group and Team Members
    await context.bot.send_message(GROUP_CHAT_ID, appointment_details)
    for member in context.user_data["selected_team"]:
        await context.bot.send_message(TEAM_MEMBERS[member], appointment_details)

    return ConversationHandler.END

# Cancel Appointment Creation
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("❌ Appointment creation canceled.")
    return ConversationHandler.END

# Conversation Handler
appointment_handler = ConversationHandler(
    entry_points=[CommandHandler("add_appointment", add_appointment)],
    states={
        CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_name)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
        START_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_datetime)],
        END_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_datetime)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
        SELECT_TEAM: [CallbackQueryHandler(select_team)],  # Only CallbackQueryHandler for buttons
        CONFIRM_APPOINTMENT: [CallbackQueryHandler(confirm_appointment)],  # Confirmation step
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Main Function
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(appointment_handler)
    app.add_handler(CommandHandler("cancel", cancel))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
