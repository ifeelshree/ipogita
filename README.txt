IPOgita - one-time setup (about 10 minutes, no coding)

What this does: every ~30 minutes a free GitHub robot reads ipowatch.in, updates the
data, and your website refreshes itself. You never touch it again.

STEP 1  Make a free GitHub account (skip if you have one): github.com -> Sign up.

STEP 2  Create the home for the site
  - Click the "+" at top right -> "New repository".
  - Name: ipogita     Visibility: Public (needed for the free website)
  - Tick "Add a README file". Click "Create repository".

STEP 3  Upload the files
  - Unzip the ipogita folder on your computer.
  - In your new repository click "Add file" -> "Upload files".
  - Open the unzipped folder and drag in EVERYTHING inside it
    (the folders "site", "scripts", ".github"). If your computer hides the
    ".github" folder, enable "show hidden files" first (Mac: Cmd+Shift+. ;
    Windows: View -> Show -> Hidden items).
  - Click "Commit changes".

STEP 4  Switch on the website
  - Repository "Settings" -> "Pages" (left menu) -> under "Build and deployment",
    set Source to "GitHub Actions".

STEP 5  Switch on the robot and the first run
  - Repository "Settings" -> "Actions" -> "General" -> "Workflow permissions"
    -> choose "Read and write permissions" -> Save.
  - Click the "Actions" tab. If asked, click "I understand my workflows, enable them".
  - Pick "Update IPO data" on the left -> "Run workflow" -> "Run workflow".
  - Then pick "Publish site" -> "Run workflow".

STEP 6  Open your site
  - Go back to Settings -> Pages. Your address is shown there:
    https://YOUR-USERNAME.github.io/ipogita/
  - Bookmark it.

If something shows a red cross in the Actions tab, open it, copy the message and
send it to Claude. The most likely cause is that ipowatch changed its page layout.
