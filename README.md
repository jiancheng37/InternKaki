# Intern Kaki - Telegram Internship Alert Bot

🚀 **Intern Kaki** is a **Telegram bot** that helps users stay updated on **new internships** in Singapore. The bot automatically scrapes job listings from **InternSG, LinkedIn (WIP), and Indeed (WIP)** and notifies users when new opportunities match their preferred roles.

---

## **✨ Features**
✅ **Automated Job Scraping** – Fetches internships from **InternSG, LinkedIn (WIP), and Indeed (WIP)**.  
✅ **Role-Based Filtering** – Users specify roles (e.g., "Software Engineer", "Data Analyst"), and only relevant jobs are sent.  
✅ **Real-Time Notifications** – New job postings are sent directly to users via Telegram.  

---

## **🛠 Tech Stack**
- **Python 3.9+**
- **Telegram Bot API (`python-telegram-bot`)**
- **PostgreSQL** (for storing users and job postings)
- **APScheduler** (for scheduled job scraping)
- **BeautifulSoup** (for web scraping)

---

## **📦 Installation & Setup**

### **1️⃣ Clone the Repository**
```sh
git clone https://github.com/jiancheng37/internkaki.git
cd internkaki
```

### **2️⃣ Install Dependencies**
```sh
pip install -r requirements.txt
```

### **3️⃣ Set Up Environment Variables (`.env`)**
Create a `.env` file and add your bot token & database credentials:
```env
BOT_TOKEN=your-telegram-bot-token
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASS=your-database-password
DB_HOST=your-database-host
DB_PORT=your-database-port
```

### **4️⃣ Start the Bot**
```sh
python3 -m bot.bot
```

---

## **📌 Usage**

### **Start the Bot**
```
/start
```
- The bot will prompt users to enter job roles.
- Example: `"Software Engineer"`, `"Data Scientist"`, etc.

### **Add More Roles**
```
/add
```
- Enter a role and press send.
- Type `"done"` when finished.

### **Remove Roles**
```
/delete
```
- The bot displays **inline buttons** with roles.
- Click a role to remove it.
- Click `"✅ Done"` to finish.

### **Stop Job Alerts**
```
/stop
```
- Unsubscribes the user and removes all stored roles.

---

## **🚀 Deployment**

### **Run in the Background (`tmux` or `screen`)**
```sh
tmux new -s internkaki
python3 -m bot.bot
```
To detach: `CTRL + B, then D`  
To reconnect: `tmux attach -t internkaki`

### **Run as a Background Process**
```sh
nohup python3 -m bot.bot & disown
```

### **Deploy to a Cloud Server**
1. **Push to GitHub**  
```sh
git push origin main
```
2. **Deploy on a Server (e.g., Railway, Heroku, AWS, etc.)**
   - Supports **Docker** for containerized deployment.
   - PostgreSQL should be hosted on **a cloud database**.

---

## **👨‍💻 Contributing**
Pull requests are welcome!  
To contribute:
1. Fork the repo & create a new branch.
2. Make your changes and commit.
3. Open a **Pull Request** with a description of your changes.

---

## **📜 License**
This project is licensed under the **MIT License**. Feel free to modify and use it!

---

## **🔗 Connect**
💬 **Telegram Bot:** [t.me/InternKakiBot](https://t.me/InternKakiBot)  
🐦 **LinkedIn:** [Low Jian Cheng](https://linkedin.com/in/lowjc)  
🌐 **Website:** [lowjiancheng.com](https://lowjiancheng.com)  

---

