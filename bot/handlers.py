import os
from scraper.scraper import scrape_internsg
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackContext, CallbackQueryHandler
)
from apscheduler.schedulers.background import BackgroundScheduler
import psycopg2
from bot.config import connect_db
import logging
import asyncio

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
scheduler = BackgroundScheduler()  # Create global scheduler instance
scheduler_started = False

# Conversation States
ROLE_ENTRY, ROLE_DELETE, ROLE_ADD = range(3)

# --- 1️⃣ /start Command ---
async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:

        logging.info(f"✅ /start command received from user {chat_id}")

        conn = connect_db()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
        user = cursor.fetchone()
        if user:
            logging.info(f"🔔 User {chat_id} is already subscribed.")
            await update.message.reply_text("You're already subscribed! You'll receive job alerts.")
            conn.close()
            return ConversationHandler.END

        conn.close()
        context.user_data["roles"] = []
        logging.info(f"🛠 Asking user {chat_id} for job preferences.")
        await update.message.reply_text("Welcome! Please enter the first role you're interested in (e.g., Software, Finance). Type 'done' when finished.")

        return ROLE_ENTRY
    except Exception as e:
        logging.error(f"❌ Error in start(): {e}", exc_info=True)

# --- 2️⃣ Collect Job Roles & Start Alerts ---
async def collect_role(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        role = update.message.text.strip().lower()
        logging.info(f"📝 User {chat_id} entered role: {role}")

        if "roles" not in context.user_data:
            context.user_data["roles"] = []  # Ensure roles list exists
            logging.info(f"🔹 Initialized roles list for user {chat_id}")

        if role == "done":
            roles = context.user_data["roles"]

            if not roles:  # Prevents empty role submission
                logging.warning(f"⚠️ User {chat_id} tried to finish without adding roles.")
                await update.message.reply_text("You haven't added any roles yet! Please enter at least one.")
                return ROLE_ENTRY
            
            logging.info(f"✅ User {chat_id} finalized roles: {roles}")
            conn = connect_db()
            cursor = conn.cursor()

            # Store user preferences in PostgreSQL
            cursor.execute("""
                INSERT INTO users (chat_id, roles) VALUES (%s, %s)
                ON CONFLICT (chat_id) DO UPDATE SET roles = EXCLUDED.roles
            """, (chat_id, roles))
            conn.commit()
            conn.close()
            logging.info(f"💾 Saved user {chat_id} roles to database: {roles}")

            await update.message.reply_text(f"You're subscribed! You'll receive job alerts for: {', '.join(roles)}.")

            # Start job alerts only for this user
            start_user_scheduler(chat_id)
            logging.info(f"🚀 Started job alerts for user {chat_id}")

            return ConversationHandler.END
        elif len(context.user_data["roles"]) >= 5:
            logging.warning(f"⚠️ User {chat_id} tried to enter more than 5 roles.")
            await update.message.reply_text("You can only enter up to 5 roles. Type 'done' to finish.")
            return ROLE_ENTRY
        elif role in context.user_data["roles"]:
            logging.warning(f"⚠️ User {chat_id} entered duplicate role: {role}")
            await update.message.reply_text(f"You've already entered '{role}'. Try another role or type 'done' when finished.")
            return ROLE_ENTRY

        else:
            context.user_data["roles"].append(role)
            logging.info(f"➕ Added role '{role}' for user {chat_id}")
            await update.message.reply_text("Got it! Enter another role or type 'done' when you're finished.")
            return ROLE_ENTRY
    except Exception as e:
        logging.error(f"❌ Error in collect_role(): {e}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again later.")
        return ROLE_ENTRY
    
async def delete_role(update: Update, context: CallbackContext):
    """Starts the delete role process by showing the user their roles."""
    chat_id = update.message.chat_id
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch user's current roles
    cursor.execute("SELECT roles FROM users WHERE chat_id = %s", (chat_id,))
    user_data = cursor.fetchone()
    conn.close()

    if not user_data or not user_data[0]:
        await update.message.reply_text("⚠️ You don't have any roles to delete.")
        return ConversationHandler.END

    roles = user_data[0]  # Assuming roles are stored as a PostgreSQL array (TEXT[])

    # Generate buttons for each role
    keyboard = [[InlineKeyboardButton(role, callback_data=f"delete_{role}")] for role in roles]
    keyboard.append([InlineKeyboardButton("✅ Done", callback_data="done_deleting")])  # Add Done button

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🗑 Select roles to delete:", reply_markup=reply_markup)

    return ROLE_DELETE

    
async def handle_delete_role(update: Update, context: CallbackContext):
    """Handles the button click event for deleting roles."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    chat_id = query.message.chat_id
    role_to_delete = query.data.replace("delete_", "")  # Extract role name from callback data

    conn = connect_db()
    cursor = conn.cursor()

    # ✅ Remove the role from the user's list
    cursor.execute("UPDATE users SET roles = array_remove(roles, %s) WHERE chat_id = %s", (role_to_delete, chat_id))
    conn.commit()

    # ✅ Fetch updated roles
    cursor.execute("SELECT roles FROM users WHERE chat_id = %s", (chat_id,))
    updated_roles = cursor.fetchone()[0]  # Extract list from tuple
    conn.close()

    # ✅ If no roles remain, end the conversation
    if not updated_roles:
        await query.edit_message_text("✅ All roles deleted. You have no roles left.")
        return ConversationHandler.END

    # ✅ Regenerate updated buttons with remaining roles
    keyboard = [[InlineKeyboardButton(role, callback_data=f"delete_{role}")] for role in updated_roles]
    keyboard.append([InlineKeyboardButton("✅ Done", callback_data="done_deleting")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🗑 Select roles to delete:", reply_markup=reply_markup)

    return ROLE_DELETE  # Stay in delete state


async def done_deleting(update: Update, context: CallbackContext):
    """Handles the 'Done' button click and exits the delete process."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Role deletion completed.")

    return ConversationHandler.END

async def add_role(update: Update, context: CallbackContext):
    """Starts the role addition process."""
    chat_id = update.message.chat_id
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch user's current roles
    cursor.execute("SELECT roles FROM users WHERE chat_id = %s", (chat_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        logging.warning(f"⚠️ User {chat_id} not found in database.")
        await update.message.reply_text("⚠️ You need to subscribe to job alerts first.")
        return ConversationHandler.END
    else:
        existing_roles = user_data[0] if user_data[0] else []

    conn.close()

    context.user_data["roles"] = existing_roles  # Store current roles in memory

    await update.message.reply_text("Enter a role to add. Type 'done' when finished.")

    return ROLE_ENTRY  # Transition to role addition state

# --- 3️⃣ Function to Start Job Alerts for a Specific User ---
def start_user_scheduler(chat_id=None):
    """Starts job alerts for a specific user or all users globally on bot start."""
    global scheduler_started
    
    if chat_id:
        job_id = f"job_{chat_id}"
        
        # Prevent duplicate jobs
        if scheduler.get_job(job_id):
            return
        
        scheduler.add_job(schedule_check_jobs_for_user, "interval", minutes=1, args=[chat_id], id=job_id)
        logging.info(f"✅ Scheduled job alerts for user {chat_id}")
    
    else:
        # Start checking jobs for ALL subscribed users
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users")
        all_users = cursor.fetchall()
        conn.close()
        
        for user in all_users:
            chat_id = user[0]
            job_id = f"job_{chat_id}"
            
            if not scheduler.get_job(job_id):
                scheduler.add_job(schedule_check_jobs_for_user, "interval", minutes=1, args=[chat_id], id=job_id)
                logging.info(f"✅ Scheduled job alerts for user {chat_id}")

    # Only start the scheduler if it's not already running
    if not scheduler_started:
        scheduler.start()
        scheduler_started = True
        logging.info("🚀 Scheduler started successfully!")


# --- 4️⃣ Check Jobs Only for This User ---
async def check_jobs_for_user(chat_id):
    """Fetches new job postings and sends alerts only for jobs the user hasn't seen."""
    logging.info(f"🔍 Checking jobs for user {chat_id}")
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Get user preferences
        cursor.execute("SELECT roles FROM users WHERE chat_id = %s", (chat_id,))
        user_data = cursor.fetchone()
        if not user_data:
            logging.warning(f"⚠️ No roles found for user {chat_id}. Skipping.")
            conn.close()
            return

        roles = list(user_data[0]) if user_data[0] else []
        logging.info(f"🛠 Fetching jobs for roles: {roles}")
        # Get latest job postings from InternSG
        jobs = scrape_internsg(roles)
        cursor.execute("SELECT EXISTS (SELECT 1 FROM users_jobs_sent WHERE chat_id = %s)", (chat_id,))
        is_first_time = not cursor.fetchone()[0]

        for job in jobs:
            job_link = job["link"]

            # Check if job was already sent to this user
            cursor.execute(
                "SELECT 1 FROM users_jobs_sent WHERE chat_id = %s AND job_link = %s",
                (chat_id, job_link)
            )
            already_sent = cursor.fetchone()

            if already_sent:
                logging.info(f"🔄 Skipping already sent job: {job_link}")
                continue  # Skip already sent jobs
            if is_first_time:
                cursor.execute(
                    "INSERT INTO users_jobs_sent (chat_id, job_link, sent_at) VALUES (%s, %s, NOW())",
                    (chat_id, job_link)
                )
                conn.commit()
                logging.info(f"📌 First-time user {chat_id} - Storing job without sending: {job_link}")
                continue  # Do NOT send messages to first-time users
            
            message = f"🔥 New Job: {job['title']} at {job['company']}\n📍 Location: {job['location']}\n🕒 Duration: {job['duration']}\n📅 Posted: {job['post_date']}\n🔗 {job['link']}"
            await bot.send_message(chat_id=chat_id, text=message)
            logging.info(f"✅ Sent job alert for {job['title']} to user {chat_id}")

            # Mark this job as sent
            cursor.execute(
                "INSERT INTO users_jobs_sent (chat_id, job_link, sent_at) VALUES (%s, %s, NOW())",
                (chat_id, job_link)
            )

            cursor.execute("""
                DELETE FROM users_jobs_sent 
                WHERE chat_id = %s 
                AND job_link IN (
                    SELECT job_link FROM users_jobs_sent
                    WHERE chat_id = %s 
                    ORDER BY sent_at ASC
                    OFFSET 30
                )
            """, (chat_id, chat_id))
            conn.commit()
    except Exception as e:
        logging.error(f"❌ Error in check_jobs_for_user(): {e}", exc_info=True)
    finally:
        if conn:
            cursor.close()
            conn.close() 

def schedule_check_jobs_for_user(chat_id):
    """Synchronous wrapper for async function."""
    asyncio.run(check_jobs_for_user(chat_id)) 

# --- 5️⃣ /stop Command ---
async def stop(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    conn = connect_db()
    cursor = conn.cursor()

    # Check if the user exists
    cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
    user = cursor.fetchone()

    if not user:
        await update.message.reply_text("You are not subscribed to job alerts.")
    else:
        cursor.execute("DELETE FROM users WHERE chat_id = %s", (chat_id,))
        cursor.execute("DELETE FROM users_jobs_sent WHERE chat_id = %s", (chat_id,))
        conn.commit()
        await update.message.reply_text("You've unsubscribed from job alerts.")

    conn.close()
    return ConversationHandler.END

# --- 6️⃣ Register Handlers ---
def register_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={ROLE_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_role)]},
        fallbacks=[]
    )

    delete_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("delete_role", delete_role)],  # Start with /delete
        states={
            ROLE_DELETE: [
                CallbackQueryHandler(handle_delete_role, pattern=r"^delete_.*"),  # Handles role deletion
                CallbackQueryHandler(done_deleting, pattern="^done_deleting$")  # Done button
            ]
        },
        fallbacks=[]
    )

    add_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_role", add_role)],  # Start with /add
        states={ROLE_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_role)]},
        fallbacks=[]
    )
    app.add_handler(conv_handler)
    app.add_handler(delete_conv_handler)
    app.add_handler(add_conv_handler)
    app.add_handler(CommandHandler("stop", stop))
