# Open MedNova on your Windows laptop

1. Extract the ZIP completely. Do not run it from inside the ZIP viewer.
2. Start your MySQL service. Install Python **3.12 (64-bit)** if it is not already installed. The Windows Python launcher `py` should be available.
3. Double-click **SETUP_WINDOWS.cmd**. It installs pinned Python packages, asks for your MySQL administrator username/password, creates the database/tables, generates a restricted application account and asks you to create your MedNova admin login. There are no default passwords.
4. Double-click **START_WINDOWS.cmd**. It checks the database and opens **http://127.0.0.1:8000**. Keep the terminal window open while using MedNova.
5. Sign in with the admin email/password you just created. Add your hospital's verified identity, contact numbers and policies in **Hospital settings**, then add departments.
6. Sign out and create a doctor account. Complete its profile. Sign back in as admin and approve that doctor after checking their credentials. Repeat approval for receptionist and pharmacist accounts.
7. Sign in as the doctor and add availability. Create a patient account and request a slot. Sign in as the doctor or receptionist to confirm it. The patient can then view the confirmed appointment.

No Node.js commands are needed. Do not run `npm run dev`.

## What works locally after MySQL setup

Registration/login, permissions, approval, directories, appointment requests, rescheduling/cancellation, dashboards, prescription records, medicine inventory, private JPEG/PNG uploads and cash/bank payment records all use MySQL.

Video calls are restricted to the assigned patient and doctor. They open 10 minutes before an appointment and remain available until 30 minutes after its start. For a local review, use separate browser profiles/accounts. For different networks, connect a TURN relay and use HTTPS.

Email password reset requires SMTP settings. Online payments require your Razorpay account and credentials. PDF uploads require ClamAV. These integrations are disabled or fail clearly when not configured; they do not pretend to work. See `docs/INTEGRATIONS.md`.

## If setup stops

- **Python not found:** install Python 3.12 with the Windows launcher, then reopen setup.
- **Database connection failed:** confirm MySQL is running and your administrator username/password are correct. XAMPP's database service may be MariaDB rather than MySQL; this project targets MySQL.
- **Port 8000 is already used:** close the previous MedNova terminal window, then retry.
- **Login rejected:** use the admin email/password chosen during setup. For other users, register an account first.
- **Staff account pending:** complete the profile, then approve it through the admin account.
- **No doctors or slots:** approve a doctor, then have that doctor add availability.
- **Forgot admin password before email is configured:** in this extracted folder run `.venv\Scripts\python.exe manage.py changepassword your-admin-email`.

Never paste your `.env`, database password, SMTP password, TURN secret or payment secret into a chat or screenshot. Configure them locally. Keep your database and private uploads backed up.

Review the website locally first. Hosting and custom-domain connection are a separate next step after your approval.
