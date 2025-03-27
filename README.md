# WastingTimeBlocker

WastingTimeBlocker is a Python-based application designed to help you stay focused by blocking distracting websites and applications based on your Google Calendar events. It works by syncing with your calendar and blocking distractions during your scheduled tasks, ensuring that you remain productive throughout the day.

## Features
- Syncs with your Google Calendar using your private iCal URL.
- Blocks distracting websites and applications based on your current calendar event.
- Works on both **Mac** and **Windows** platforms.
- Runs in the background, automatically blocking and unblocking distractions based on your active tasks.
- Requires administrator privileges to run the application (needed to execute shell scripts for blocking websites/apps).

## Requirements
- Python 3.11 or higher
- Access to your Google Calendar's **iCal URL** (found in Google Calendar settings)
- Administrator privileges to run the application (needed to execute shell scripts for blocking websites/apps)

## How It Works
1. **Google Calendar Sync**: 
   The application uses your private **iCal URL** to fetch your calendar data. It will convert each calendar event into a `Task` class with specific details (such as event description, start time, and end time).

2. **Blocking Mechanism**: 
   Based on the task information, the program will block websites and applications related to the current event. It uses different blocking methods for Mac and Windows platforms.

3. **Blocking Specific Apps and Websites**: 
   If you want to block certain websites or applications for a specific task, you can include them in the event description in the following format:
   
   ```
   ##BLOCKING
   Block_apps: app1, app2, app3;
   Block_websites: website1, website2;
   ##BLOCKING
   ```
   You can use **one or both** of the blocking options (for apps and websites). The blocking list will be parsed and applied for that particular event. You can add any other text in the description, just make sure to use the exact format for blocking to work.

   - **Block_apps**: List applications you want to block (e.g., Safari, Messenger).
   - **Block_websites**: List websites you want to block (e.g., www.facebook.com).

   If no blocking options are provided, the app will not block anything, and it will run unobtrusively in the background.

4. **Background Operation**: 
   WastingTimeBlocker continuously runs in the background and constantly checks your calendar for upcoming events. When a task begins, it blocks distractions, and when the task ends, everything is unblocked.

5. **Admin Privileges**: 
   Due to the nature of the blocking mechanism, the program needs to run with administrator privileges. This is because it needs to interact with system processes to block websites and applications.

## Installation and Setup

### Step 1: Install Python 3.11
Make sure you have Python 3.11 or a later version installed.

### Step 2: Clone the Repository
Clone the repository to your local machine:

```bash
git clone https://github.com/your-username/WastingTimeBlocker.git
cd WastingTimeBlocker
```

### Step 3: Set Up Your Google Calendar iCal URL
In the `calendar_url.py` file, paste your **Google Calendar iCal URL**. You can find it by going to **Google Calendar > Settings > Integrate Calendar** and copying the **Secret address in iCal format**.

```python
# calendar_url.py

ICAL_URL = 'your_calendar_ical_url_here'
```

### Step 4: Run the Application
Run the `main.py` script to start the application:

```bash
python main.py
```

Make sure to run the script with administrator privileges. On Windows, you may need to run it as an administrator. On Mac, you may need to grant necessary permissions.

## Important Notes
- **Admin Privileges**: The app needs administrator access to block websites and applications. Ensure you have the required permissions before running the program.
- **Responsibility**: Use this tool at your own risk. The project owner is not responsible for any issues that arise while using this program. Ensure that you're comfortable with the changes it makes to your system before running it.
  
- Integration with additional calendar services.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Thank you for using WastingTimeBlocker! Stay focused and productive.
