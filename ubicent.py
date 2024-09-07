from requests import session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import sqlite3
from datetime import datetime

# Database setup
def setup_database():
    conn = sqlite3.connect('attendance.db', check_same_thread=False)
    c = conn.cursor()
    


        # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                country TEXT NOT NULL,
                country_updated INTEGER DEFAULT 0,
                referral_id INTEGER,
                FOREIGN KEY (referral_id) REFERENCES Users(id)
            )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES Users(id)
            )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                FOREIGN KEY (referrer_id) REFERENCES Users(id),
                FOREIGN KEY (referred_id) REFERENCES Users(id)
            )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Signins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                signins INTEGER DEFAULT 10,
                FOREIGN KEY (user_id) REFERENCES Users(id)
            )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Ranks (
                    user_id INTEGER PRIMARY KEY, 
                    rank TEXT, 
                    signins INTEGER,
                    global_signins INTEGER DEFAULT 0,
                    global_rank TEXT,
                    bonus_claimed BOOLEAN DEFAULT 0,
                    bonus_amount REAL DEFAULT 0
              )''')

    
    c.execute('''CREATE TABLE IF NOT EXISTS UserCompletedActivities (
                user_id INTEGER,
                activity_id INTEGER,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, activity_id),
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (activity_id) REFERENCES Activities(id)
            )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                points INTEGER NOT NULL
            )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS UserCompletedActivitiesNational (
                    user_id INTEGER,
                    nationalactivities_id INTEGER,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, nationalactivities_id),
                    FOREIGN KEY (user_id) REFERENCES Users(id),
                    FOREIGN KEY (nationalactivities_id) REFERENCES NationalActivities(id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS NationalActivities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    country TEXT NOT NULL,
                    points INTEGER NOT NULL
                )''')
   
    conn.commit()     
    return conn, c

conn, c = setup_database()


# Menu Builder
class MenuBuilder:
    @staticmethod
    def main_menu(user_id):
        # signin_button = InlineKeyboardButton("🔑 Sign In", callback_data='signin')
        # referral_button = InlineKeyboardButton("📨 Get Referral Link", callback_data='referral')
        # referral_stats_button = InlineKeyboardButton("📊 View Referral Stats", web_app={"url": f"https://695a-154-160-14-57.ngrok-free.app/referral_stats/{user_id}"})
        

        # view_app_stats = InlineKeyboardButton(
        #     "📋 View App Statistics",
        #     web_app={"url": f"https://695a-154-160-14-57.ngrok-free.app/user_signins/{user_id}"}
        # )

        # Construct the deep link for the Mini App
        deep_link = f"user_details/{user_id}"
        
        # Use the proper URL scheme for the Telegram Mini App
        dashboard_button = InlineKeyboardButton(
            "📊 View Dashboard",
            web_app={
                "url": f"https://695a-154-160-14-57.ngrok-free.app/{deep_link}"
            }
        )

        keyboard = [
            # [signin_button],
            # [referral_button],
            # [view_app_stats],
            # [referral_stats_button],
            [dashboard_button]
        ]
        
        return InlineKeyboardMarkup(keyboard)



# Handle country selection
async def select_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    selected_country = query.data.split('_')[-1]  # Extract the selected country from callback data
    
    try:
        with sqlite3.connect('attendance.db') as conn:
            c = conn.cursor()
            # Update the user's country
            c.execute("UPDATE Users SET country = ? WHERE id = ?", (selected_country, user_id))
            
            # Award the user with 5 additional sign-ins
            c.execute("UPDATE Ranks SET signins = signins + 5 WHERE user_id = ?", (user_id,))
            
            conn.commit()
            await query.edit_message_text(f"Country updated to: {selected_country}. You have been awarded 5 sign-ins. You can now proceed to the main menu with /menu.")
    except sqlite3.OperationalError as e:
        await query.edit_message_text(f"Database error: {e}")

# Update the start command to include registration form
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    username = user.username
    
    try:
        with sqlite3.connect('attendance.db') as conn:
            c = conn.cursor()
            # Insert user into the Users table if not already present
            c.execute("INSERT OR IGNORE INTO Users (id, username, country) VALUES (?, ?, '')", (user_id, username))
            c.execute("INSERT OR IGNORE INTO Ranks (user_id, rank, signins) VALUES (?, ?, ?)", (user_id, 'Unranked', 0))
            conn.commit()
            
            await update.message.reply_text(
                f"Hello {username}! Welcome to the bot. Please complete your registration by selecting your country."
            )
            
            # Instead of sending the URL, directly show the registration form
            # await registration_form(update, context)
            await menu(update, context)
    except sqlite3.OperationalError as e:
        await update.message.reply_text(f"Database error: {e}")

async def signin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    
    date = datetime.now().strftime('%Y-%m-%d')
    time = datetime.now().strftime('%H:%M:%S')
    
    try:
        with sqlite3.connect('attendance.db') as conn:
            c = conn.cursor()
            # Check if the user has already signed in today
            c.execute("SELECT id FROM Attendance WHERE user_id = ? AND date = ?", (user_id, date))
            existing_entry = c.fetchone()
            
            if existing_entry:
                await query.edit_message_text("You have already signed in today.")
            else:
                # Insert sign-in record
                c.execute("INSERT INTO Attendance (user_id, date, time) VALUES (?, ?, ?)", (user_id, date, time))
                conn.commit()
                
                # Update rank or other relevant data
                c.execute("UPDATE Ranks SET signins = signins + 5 WHERE user_id = ?", (user_id,))
                conn.commit()
                
                await query.edit_message_text("Sign-in successful! Your progress has been recorded.")
    except sqlite3.OperationalError as e:
        await query.edit_message_text(f"Database error: {e}")

# Main menu command
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id

    # Build the main menu with the user's ID
    reply_markup = MenuBuilder.main_menu(user_id)
    
  # Send the image
    await update.message.reply_photo(
        photo='https://ibb.co/TvSBF6J',  # Replace with the URL or local path to your image
        caption=(
            "The UBI-Cent initiative will transition into the UBI-Dollar stablecoin on our own blockchain. "
            "Our goal is to provide a Universal Basic Income of at least $144 per user once we reach 1.44 billion users. "
            "In the meantime, a total of $300 million UBI-Dollar stablecoins will be airdropped to individuals, "
            "and 100 million to celebrities and influencers who help onboard the next billion on-chain users.\n\n"
            "The UBIC & UBID teams are developing a blockchain focused on regenerative tokenization within the "
            "Environmental, Social, and Governance (ESG) framework, aiming to create a vast, ESG-compliant ecosystem. "
            "Engage seriously in the tasks and secure your share of the $300 million airdrop for individuals and "
            "$100 million for celebrities and influencers."
        ),
        reply_markup=reply_markup
    )




async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    
    # Create a referral link
    referral_link = f"https://t.me/m2e2bot?start={user_id}"
    
    await update.message.reply_text(
        f"Invite your friends using this link: {referral_link}\nFor each successful referral, you will earn 10 sign-ins."
    )

async def start_with_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    username = user.username
    
    # Check if there's a referral ID in the start command
    referral_id = context.args[0] if context.args else None
    
    try:
        with sqlite3.connect('attendance.db') as conn:
            c = conn.cursor()
            # Insert user into the Users table if not already present
            c.execute("INSERT OR IGNORE INTO Users (id, username, country, referral_id) VALUES (?, ?, '', ?)", (user_id, username, referral_id))
            c.execute("INSERT OR IGNORE INTO Ranks (user_id, rank, signins) VALUES (?, ?, ?)", (user_id, 'Unranked', 0))
            conn.commit()
            
            # Handle referral bonus
            if referral_id:
                # Check if the referrer exists
                c.execute("SELECT id FROM Users WHERE id = ?", (referral_id,))
                referrer = c.fetchone()
                
                if referrer:
                    # Award 10 sign-ins to the referrer
                    c.execute("INSERT INTO Referrals (referrer_id, referred_id) VALUES (?, ?)", (referral_id, user_id))
                    c.execute("UPDATE Ranks SET signins = signins + 10 WHERE user_id = ?", (referral_id,))
                    conn.commit()
                    
            await update.message.reply_text(
                f"Hello {username}! Welcome to the UBI-Cent."
                "The UBI-Cent initiative will transition into the UBI-Dollar stablecoin on our own blockchain. "
                "Our goal is to provide a Universal Basic Income of at least $144 per user once we reach 1.44 billion users. "
            )
            
            # Show the registration form
            await menu(update, context)
    except sqlite3.OperationalError as e:
        await update.message.reply_text(f"Database error: {e}")


# Command handlers setup
def main():
    application = Application.builder().token("7515337922:AAFvnBgsw_bbYLIL5TwzFW118HUlumhMxKE").build()

    application.add_handler(CommandHandler("start", start_with_referral))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(signin_callback, pattern="signin"))
    application.add_handler(CallbackQueryHandler(referral_callback, pattern="referral"))
    application.add_handler(CallbackQueryHandler(select_country_callback, pattern="select_country_"))
    
    application.run_polling()

if __name__ == "__main__":
    main()

