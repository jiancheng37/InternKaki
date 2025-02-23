import os
from scraper.scraper import scrape_internsg
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackContext, CallbackQueryHandler
)
from apscheduler.schedulers.background import BackgroundScheduler
from bot.config import connect_db
import logging
import asyncio
import time

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
scheduler = BackgroundScheduler()  # Create global scheduler instance
scheduler_started = False

# Conversation States
ROLE_ENTRY, ASK_NAME, ASK_EMAIL, ASK_CONTACT, ASK_START_DATE, ASK_END_DATE, ASK_SUMMARY, ROLE_DELETE, ROLE_ADD = range(7)

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
            await update.message.reply_text("Great! Now, let's collect your personal details. What's your full name?")
            return ASK_NAME

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
    
async def collect_name(update: Update, context: CallbackContext):
    """Collects user's full name."""
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Got it! Now, enter your email address.")
    return ASK_EMAIL

async def collect_email(update: Update, context: CallbackContext):
    """Collects user's email."""
    context.user_data["email"] = update.message.text.strip()
    await update.message.reply_text("Thanks! Now, enter your contact number.")
    return ASK_CONTACT

async def collect_contact(update: Update, context: CallbackContext):
    """Collects user's contact number."""
    context.user_data["contact"] = update.message.text.strip()
    await update.message.reply_text("Great! When are you available to start? (Format: DD-MM-YYYY)")
    return ASK_START_DATE

async def collect_start_date(update: Update, context: CallbackContext):
    """Collects user's availability start date."""
    context.user_data["start_date"] = update.message.text.strip()
    await update.message.reply_text("Got it! When is your last available date? (Format: DD-MM-YYYY)")
    return ASK_END_DATE

async def collect_end_date(update: Update, context: CallbackContext):
    """Collects user's availability end date."""
    context.user_data["end_date"] = update.message.text.strip()
    await update.message.reply_text("Almost done! Please provide a short text CV summary (e.g., skills, experience).")
    return ASK_SUMMARY

async def collect_summary(update: Update, context: CallbackContext):
    """Collects user's executive summary."""
    context.user_data["summary"] = update.message.text.strip()

    # Save all user data to the database
    chat_id = update.message.chat_id
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (chat_id, roles, name, email, contact, start_date, end_date, summary) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                chat_id,
                context.user_data["roles"],
                context.user_data["name"],
                context.user_data["email"],
                context.user_data["contact"],
                context.user_data["start_date"],
                context.user_data["end_date"],
                context.user_data["summary"],
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()

        await update.message.reply_text("✅ Registration complete! You'll now receive job alerts automatically.")
        start_user_scheduler(chat_id)
        logging.info(f"🎉 User {chat_id} successfully registered.")
        return ConversationHandler.END

    except Exception as e:
        logging.error(f"❌ Error saving user {chat_id} to database: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred while saving your data. Please try again.")
        return ConversationHandler.END
    
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
        
        scheduler.add_job(schedule_check_jobs_for_user, "interval", minutes=20, args=[chat_id], id=job_id)
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
                scheduler.add_job(schedule_check_jobs_for_user, "interval", minutes=20, args=[chat_id], id=job_id)
                logging.info(f"✅ Scheduled job alerts for user {chat_id}")

    # Only start the scheduler if it's not already running
    if not scheduler_started:
        scheduler.start()
        scheduler_started = True
        logging.info("🚀 Scheduler started successfully!")


# --- 4️⃣ Check Jobs Only for This User ---
async def check_and_apply_jobs_for_user(chat_id):
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
            
async def apply_for_job(job_url, chat_id):
    """Determines the application method and applies accordingly."""
    application_method, application_info = extract_application_method(job_url)

    if application_method == "email":
        message = f"📌 This job requires **email application**.\n📧 Please send your CV to: {application_info}\n🔗 Job Link: {job_url}"
        await bot.send_message(chat_id=chat_id, text=message)
        logging.info(f"📧 Notified user {chat_id} to apply via email: {application_info}")
        return False  # Application not automated

    elif application_method == "internsg":
        logging.info(f"✅ Proceeding with InternSG automated application for {job_url}")

        # Extract the direct application form URL
        application_form_url = extract_application_url(job_url)
        if not application_form_url:
            return False  

        # Fetch user data from the database
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, email, contact, start_date, end_date, summary 
            FROM users 
            WHERE chat_id = %s
        """, (chat_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()

        # Validate that all necessary fields are filled
        if not user_data or None in user_data:
            logging.error(f"❌ Missing user data for chat_id {chat_id}. Cannot proceed.")
            await bot.send_message(chat_id=chat_id, text="❌ Your profile is incomplete. Please update your details using /edit_profile.")
            return False

        # Map database results to field names
        user_profile = {
            "name": user_data[0],
            "email": user_data[1],
            "contact": user_data[2],
            "availability": f"From {user_data[3]} - {user_data[4]}",  # Start & End date formatted
            "summary": user_data[5]
        }

        # Now, fill out the form
        success = fill_application_form(application_form_url, user_profile)
        return success

    elif application_method == "website":
        message = f"🌐 This job requires application via the **company's website**.\n🔗 Apply here: {application_info}\n🔗 Job Link: {job_url}"
        await bot.send_message(chat_id=chat_id, text=message)
        logging.info(f"🌐 Notified user {chat_id} to apply via company website: {application_info}")
        return False  # Application not automated

    else:
        logging.warning(f"⚠️ Unknown application method for {job_url}")
        return False


def extract_application_method(job_url):
    """Checks the job page for application instructions and determines the correct method."""
    logging.info(f"🔄 Checking application method for: {job_url}")

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(job_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all divs with class "ast-row p-3"
    application_sections = soup.find_all("div", class_="ast-row p-3")

    for section in application_sections:
        # Check if this section contains "Application Instructions"
        label = section.find("div", class_="ast-col-md-2 font-weight-bold")
        content = section.find("div", class_="ast-col-md-10")

        if label and "Application Instructions" in label.get_text(strip=True):
            application_text = content.get_text(strip=True)
            logging.info(f"📌 Application instructions: {application_text}")

            # Check if the job requires email application
            if "email" in application_text.lower():
                email = None
                words = application_text.split()
                for word in words:
                    if "@" in word:  # Likely an email address
                        email = word.strip()
                        break
                return "email", email  # Notify user to apply via email

            # Check if it allows InternSG application
            if "text cv using internsg" in application_text.lower():
                return "internsg", None  # Proceed with automation

            # Check if the job requires applying via an external company website
            for link in content.find_all("a", href=True):
                if "http" in link["href"]:  # Ensure it's an external link
                    return "website", link["href"]  # Notify user to apply via this website

    logging.warning(f"⚠️ No clear application method found for {job_url}")
    return None, None  # Unknown application method

def extract_application_url(job_url):
    """Extracts the direct application link from the job details page."""
    logging.info(f"🔄 Extracting application URL from: {job_url}")

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(job_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the "Apply for this position" button
    apply_button = soup.find("a", class_="ast-button btn-block btn-apply")

    if apply_button and "href" in apply_button.attrs:
        application_url = f"https://www.internsg.com{apply_button['href']}"
        logging.info(f"✅ Extracted application link: {application_url}")
        return application_url

    logging.warning(f"⚠️ No application link found on {job_url}")
    return None

def fill_application_form(application_url, user_data):
    """Fills out and submits the job application form automatically."""
    logging.info(f"📝 Filling out application form: {application_url}")

    # Setup Selenium WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service("/opt/homebrew/bin/chromedriver")  # Update path if needed
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Step 1: Open the application form page
        driver.get(application_url)
        time.sleep(3)  # Allow page to load

        # Step 2: Fill out the form
        driver.find_element(By.ID, "applicant_name").send_keys(user_data["name"])
        driver.find_element(By.ID, "applicant_email").send_keys(user_data["email"])
        driver.find_element(By.ID, "applicant_contact").send_keys(user_data["contact"])
        driver.find_element(By.ID, "applicant_period").send_keys(user_data["availability"])
        driver.find_element(By.ID, "applicant_summary").send_keys(user_data["summary"])

        # Step 3: Submit the application
        submit_button = driver.find_element(By.ID, "btnSubmit")
        submit_button.click()
        logging.info(f"✅ Application submitted successfully: {application_url}")

        driver.quit()
        return True  # Application successful

    except Exception as e:
        logging.error(f"❌ Error filling application for {application_url}: {e}")
        driver.quit()
        return False  # Application failed


def schedule_check_jobs_for_user(chat_id):
    """Synchronous wrapper for async function."""
    asyncio.run(check_jobs_for_user(chat_id)) 

async def edit_profile(update: Update, context: CallbackContext):
    """Allows users to edit their profile details."""
    chat_id = update.message.chat_id
    logging.info(f"📝 User {chat_id} is editing their profile.")

    # Create buttons for each field the user can edit
    keyboard = [
        [InlineKeyboardButton("📝 Name", callback_data="edit_name")],
        [InlineKeyboardButton("📧 Email", callback_data="edit_email")],
        [InlineKeyboardButton("📞 Contact Number", callback_data="edit_contact")],
        [InlineKeyboardButton("📅 Start Date", callback_data="edit_start_date")],
        [InlineKeyboardButton("📅 End Date", callback_data="edit_end_date")],
        [InlineKeyboardButton("📜 Executive Summary", callback_data="edit_summary")],
        [InlineKeyboardButton("✅ Done", callback_data="done_editing")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Which detail would you like to edit?", reply_markup=reply_markup)

async def handle_edit_choice(update: Update, context: CallbackContext):
    """Handles which field the user wants to edit."""
    query = update.callback_query
    await query.answer()
    
    field_map = {
        "edit_name": ASK_NAME,
        "edit_email": ASK_EMAIL,
        "edit_contact": ASK_CONTACT,
        "edit_start_date": ASK_START_DATE,
        "edit_end_date": ASK_END_DATE,
        "edit_summary": ASK_SUMMARY
    }

    if query.data in field_map:
        await query.edit_message_text(f"Enter your new {query.data.replace('edit_', '').replace('_', ' ')}:")
        return field_map[query.data]

    elif query.data == "done_editing":
        await query.edit_message_text("✅ Profile update complete.")
        return ConversationHandler.END

    return ConversationHandler.END

async def update_name(update: Update, context: CallbackContext):
    """Updates the user's name."""
    new_name = update.message.text.strip()
    chat_id = update.message.chat_id

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = %s WHERE chat_id = %s", (new_name, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text(f"✅ Your name has been updated to: {new_name}")
    return ConversationHandler.END

async def update_email(update: Update, context: CallbackContext):
    """Updates the user's email."""
    new_email = update.message.text.strip()
    chat_id = update.message.chat_id

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET email = %s WHERE chat_id = %s", (new_email, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text(f"✅ Your email has been updated to: {new_email}")
    return ConversationHandler.END

async def update_contact(update: Update, context: CallbackContext):
    """Updates the user's contact number."""
    new_contact = update.message.text.strip()
    chat_id = update.message.chat_id

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET contact = %s WHERE chat_id = %s", (new_contact, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text(f"✅ Your contact number has been updated to: {new_contact}")
    return ConversationHandler.END

async def update_start_date(update: Update, context: CallbackContext):
    """Updates the user's availability start date."""
    new_start_date = update.message.text.strip()
    chat_id = update.message.chat_id

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET start_date = %s WHERE chat_id = %s", (new_start_date, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text(f"✅ Your availability start date has been updated to: {new_start_date}")
    return ConversationHandler.END

async def update_end_date(update: Update, context: CallbackContext):
    """Updates the user's availability end date."""
    new_end_date = update.message.text.strip()
    chat_id = update.message.chat_id

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET end_date = %s WHERE chat_id = %s", (new_end_date, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text(f"✅ Your availability end date has been updated to: {new_end_date}")
    return ConversationHandler.END

async def update_summary(update: Update, context: CallbackContext):
    """Updates the user's executive summary."""
    new_summary = update.message.text.strip()
    chat_id = update.message.chat_id

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET summary = %s WHERE chat_id = %s", (new_summary, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text("✅ Your executive summary has been updated.")
    return ConversationHandler.END

# --- /stop Command ---
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

# --- Register Handlers ---
def register_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROLE_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_role)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_name)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_email)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_contact)],
            ASK_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_start_date)],
            ASK_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_end_date)],
            ASK_SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_summary)],
        },
        fallbacks=[],
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

    edit_profile_handler = ConversationHandler(
    entry_points=[CommandHandler("edit_profile", edit_profile)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_name)],
        ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_email)],
        ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_contact)],
        ASK_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_start_date)],
        ASK_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_end_date)],
        ASK_SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_summary)],
    },
    fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(delete_conv_handler)
    app.add_handler(add_conv_handler)
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(edit_profile_handler)
    app.add_handler(CallbackQueryHandler(handle_edit_choice, pattern="^edit_.*|^done_editing$"))
