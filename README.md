# 🏡 GramSeva

A digital service kiosk platform designed to make essential online services easily accessible through a simple, role-based interface.

## ✨ Features

- 👤 **Resident Login & Registration**
- 🧑‍💼 **Kiosk Operator Login**
- 🛡️ **Admin Login**
- 📋 Service request management
- 🔄 Request status tracking
- 🎉 Completion animation for processed requests
- 📊 Interactive Plotly analytics
- 🌈 Animated and colorful UI
- 🗄️ SQLite database
- 🔐 Password hashing and role-based access
- 📱 Responsive Streamlit interface

## 👥 User Roles

### 👤 Resident
- Create an account
- Browse available services
- Submit service requests
- Track request status
- View request history

### 🧑‍💼 Kiosk Operator
- View incoming requests
- Process resident requests
- Update request status
- Mark requests as completed
- Manage the active request queue

### 🛡️ Admin
- Manage requests
- Monitor residents
- View revenue analytics
- View service usage
- View request statistics
- Access the complete dashboard

## 🛠️ Tech Stack

- **Python**
- **Streamlit**
- **Pandas**
- **Plotly**
- **SQLite**
- **HTML/CSS**
- **Git & GitHub**

## 📂 Project Structure

```text
GramSeva/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── gramseva.db        # created automatically, not committed
````

## 🚀 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/GramSeva.git
cd GramSeva
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
python -m streamlit run app.py
```

The application will open at:

```text
http://localhost:8501
```

## 🔑 Demo Login

### 🛡️ Admin

```text
ID: admin
Password: admin123
```

### 🧑‍💼 Kiosk Operator

```text
ID: operator
Password: operator123
```

### 👤 Resident

Residents can create an account using the **Resident Sign Up** option.

## 📊 Analytics

The Admin dashboard includes interactive Plotly visualizations for:

* 📈 Daily Revenue
* 💰 Revenue by Service
* 🥧 Service Usage
* 📋 Request Status

## 🔄 Request Flow

```text
Resident
   ↓
Submit Request
   ↓
Submitted
   ↓
Kiosk Operator
   ↓
In Progress
   ↓
Completed
   ↓
🎉 Completion Animation
   ↓
Removed from Active Queue
```

Completed requests remain stored in the database for history and analytics.

## 🗄️ Database

GramSeva uses **SQLite** for local data storage.

The database is automatically created when the application starts.

The database file is excluded from GitHub using `.gitignore`.

## 🎨 UI

The application includes:

* Animated cards
* Gradient sections
* Hover effects
* Colorful tables
* Interactive charts
* Animated completion feedback
* Role-specific navigation

## 📌 Project Status

🟢 **Active Development**

Core authentication, service requests, role-based access, request management, animations, database integration, and analytics are implemented.

## 👩‍💻 Author

**Jahnvi Srivastava**

⭐ If you like this project, consider giving it a star!

