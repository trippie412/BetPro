# BetPro - Premium Sports Betting Platform

A full-featured, enterprise-grade sports betting platform built with Python Flask, featuring a modern dark UI with glassmorphism design, Blue & Gold theme, and comprehensive betting engine.

## Features

### 🎯 Core Betting
- Single and Accumulator (Parlay) bets
- Real-time odds display
- Live betting support
- Bet slip management
- Automatic bet settlement
- Configurable odds and markets

### 👤 User Management
- Registration with email and phone
- Secure authentication (password hashing, CSRF)
- Email verification structure
- Password reset flow
- User profiles with avatars
- Role-based access (User, Admin, Super Admin)

### 💰 Wallet System
- Cash balance and bonus balance
- Deposit management
- Withdrawal requests
- Full transaction ledger
- Welcome bonus (KES 1,000 on first deposit of KES 500+)
- Admin wallet adjustments

### 🏆 Sports Coverage
- Football, Basketball, Tennis
- Volleyball, Rugby, eSports
- Virtual Games
- Multiple leagues per sport
- Featured and live match indicators

### 📊 Admin Panel
- Full user management (suspend/activate)
- Deposit/withdrawal approval workflow
- Match and odds management
- Sports and leagues CRUD
- System-wide announcements
- Audit logging
- Analytics dashboard
- Configurable system settings

### 🎨 Design
- Dark theme with Blue & Gold accents
- Glassmorphism card design
- Responsive (Desktop, Tablet, Mobile)
- Smooth animations
- Professional sportsbook layout
- Chart.js integration for analytics

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, Flask |
| Database | SQLite (Dev), PostgreSQL (Prod) |
| ORM | SQLAlchemy, Flask-Migrate |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5 |
| Charts | Chart.js |
| Auth | Flask-Login, Werkzeug Security |
| Forms | Flask-WTF, WTForms |
| Security | CSRF, XSS Protection, Rate Limiting |
| Server | Gunicorn (Production) |

## Project Structure