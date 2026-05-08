import os
import re
import shutil
import zipfile
import webbrowser
import subprocess
import threading
import textwrap
from pathlib import Path
from urllib.request import urlretrieve
from tqdm import tqdm
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
import winreg
import requests
import sys
import time

def balala():
    try:
        output = subprocess.check_output(
            ["wmic", "process", "get", "name"],
            creationflags=subprocess.CREATE_NO_WINDOW
        ).decode(errors="ignore").lower()

        return any(line.strip() == "balatro.exe" for line in output)
    except:
        return False
    
def iCanHazDL(url, dest_path):
    def hook(t):
        last_b = [0]
        def update(b=1, bsize=1, tsize=None):
            if tsize is not None: t.total = tsize
            t.update((b - last_b[0]) * bsize)
            last_b[0] = b
        return update
    with tqdm(unit='B', unit_scale=True, miniters=1, desc=Path(dest_path).name) as t:
        urlretrieve(url, dest_path, reporthook=hook(t))


def iCanHazBalatroDir():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path = Path(winreg.QueryValueEx(key, "SteamPath")[0].replace("\\\\", "\\"))
        winreg.CloseKey(key)
        for lib in [steam_path] + iCanHazSteamLibrary()[1:]:
            path = lib / "steamapps" / "common" / "Balatro"
            if path.exists():
                return path
    except:
        pass
    return None


def iCanHazSteamLibrary():
    libraries = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path = Path(winreg.QueryValueEx(key, "SteamPath")[0].replace("\\\\", "\\"))
        winreg.CloseKey(key)
        libraries.append(steam_path)
        vdf = steam_path / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            content = vdf.read_text(encoding="utf-8")
            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            for p in paths:
                lib = Path(p.replace("\\\\", "\\"))
                if lib not in libraries:
                    libraries.append(lib)
    except:
        pass
    return libraries


def iCanHazReleases(repo: str, per_page=15):
    resp = requests.get(f"https://api.github.com/repos/{repo}/releases?per_page={per_page}")
    resp.raise_for_status()
    return resp.json()


def iCanHazDLnUnzip(release, target_dir: Path, versioned_name=None):
    target_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = Path("temp_downloads")
    temp_dir.mkdir(exist_ok=True)

    try:
        if release.get('assets'):
            zip_assets = [a for a in release['assets'] if a['name'].endswith('.zip')]
            asset = zip_assets[0] if zip_assets else release['assets'][0]
            download_url = asset['browser_download_url']
            filename = Path(asset['name'])
        else:
            download_url = release['zipball_url']
            filename = Path(f"{release['tag_name']}.zip")

        temp_file = temp_dir / filename

        iCanHazDL(download_url, temp_file)

        extract_temp = temp_dir / "extract_temp"
        extract_temp.mkdir(exist_ok=True)

        with zipfile.ZipFile(temp_file) as zf:
            zf.extractall(extract_temp)

        items = list(extract_temp.iterdir())
        source = extract_temp if len(items) != 1 or not items[0].is_dir() else items[0]

        final_target = target_dir / versioned_name if versioned_name else target_dir
        final_target.mkdir(exist_ok=True)

        for item in source.iterdir():
            dest = final_target / item.name
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True) if dest.is_dir() else dest.unlink()
            shutil.move(item, dest)

        temp_file.unlink(missing_ok=True)
        shutil.rmtree(extract_temp, ignore_errors=True)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return final_target

class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ezInstaller")
        w = int(self.winfo_screenwidth() * 0.25)
        h = int(self.winfo_screenheight() * 0.25)
        self.rot_text = self.retroslopText("ezInstaller")
        self.geometry(f"{w}x{h}")
        self.minsize(650, 420)
        self.resizable(False, False)
        self.configure(bg="#c0c0c0")

        self.default_font = ("MS Sans Serif", 10)
        self.title_font = ("MS Sans Serif", 12, "bold")

        self.balatro_dir = iCanHazBalatroDir()
        self.choice = None
        self.selected_release = None
        self.game_dir_var = tk.StringVar()
        if self.balatro_dir:
            self.game_dir_var.set(str(self.balatro_dir))
        self.launch_var = tk.BooleanVar(value=True)
        self.lovely_releases = []
        self.lovely_release = None
        self.releases = []
        self.mods_base = Path(os.getenv("APPDATA")) / "Balatro" / "Mods"
        self.installing = False

        self.iCanHazLayout()
        self.pageIntro()
        
    def retroslopGradient(self, event=None):
        self.header_canvas.delete("all")

        width = self.header_canvas.winfo_width()
        height = self.header_canvas.winfo_height()

        r1, g1, b1 = 0, 0, 255
        r2, g2, b2 = 0, 0, 39

        for i in range(height):
            t = i / height

            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)

            color = f"#{r:02x}{g:02x}{b:02x}"
            self.header_canvas.create_line(0, i, width, i, fill=color)

        self.header_canvas.create_image(
            10,
            height - 10,
            image=self.rot_text,
            anchor="sw"
        )
            
    def retroslopText(self, text):
        try:
            font = ImageFont.truetype("timesbi.ttf", 28)
        except:
            font = ImageFont.load_default()

        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        w, h = draw.textbbox((0, 0), text, font=font)[2:]

        pad = 20
        img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        x, y = pad, pad

        shadow_offset = 2
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            text,
            font=font,
            fill=(0, 0, 0, 180)
        )

        draw.text(
            (x, y),
            text,
            font=font,
            fill=(255, 255, 255, 255)
        )

        rotated = img.rotate(90, expand=True)

        return ImageTk.PhotoImage(rotated)


    
    def iCanHazLicense(self, url):
        webbrowser.open(url)
        
    def canYouCloseTheDamnGameYet(self):
        print("STEP: Waiting for Balatro to close...")

        while balala():
            time.sleep(1)

        
    def whereIsBalatro(self):
        folder = filedialog.askdirectory(
            title="Select Balatro Directory",
            initialdir=self.game_dir_var.get() or "/"
        )

        if folder:
            self.game_dir_var.set(folder)
    

    
    def finish_installer(self):
        if self.launch_var.get() and self.balatro_dir:
            exe = self.balatro_dir / "Balatro.exe"

            if exe.exists():
                subprocess.Popen([str(exe)])

        self.destroy()
        
    def justLetMeMakeSureYouOwnTheGame(self):
        folder = Path(self.game_dir_var.get())
        
        folder_str = self.game_dir_var.get().strip()

        if not folder_str:
            messagebox.showerror("Error", "Please select a game folder.")
            return

        folder = Path(folder_str)

        exe = folder / "Balatro.exe"

        if not exe.exists():
            messagebox.showerror(
                "Invalid Folder",
                "Balatro.exe was not found in this folder.\n\nPlease select your Balatro installation directory."
            )
            return
        
        self.balatro_dir = folder

        if self.choice in [1, 3]:
            self.pageLovely()
        else:
            self.pageSmods()

    def caniMoveThisOverHere(self):
        folder = filedialog.askdirectory(title="Select Mods Folder", initialdir=self.mods_base)
        if folder:
            self.mods_base = Path(folder)
            self.dir_var.set(str(self.mods_base))

    def letmegetthatSmods(self, event=None):
        index = self.version_combo.current()
        if index >= 0:
            self.selected_release = self.releases[index]
            self.next_btn.config(state="normal")
            
    def letmegetthatInjector(self, event=None):
        index = self.lovely_version_combo.current()
        if index >= 0:
            self.lovely_release = self.lovely_releases[index]
            self.next_btn.config(state="normal")
        
    def iCanHazSmods(self):
        try:
            self.releases = iCanHazReleases("Steamodded/smods", 10)

            items = [
                f"{r['tag_name']}{' (latest)' if i==0 else ''}{' [PRE]' if r.get('prerelease') else ''}"
                for i, r in enumerate(self.releases)
            ]

            def apply():
                self.version_combo.configure(values=items)

                if items:
                    self.version_combo.current(0)
                    self.selected_release = self.releases[0]

                self.next_btn.config(state="normal")
                self.status.config(text="")

            self.after(0, apply)

        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", str(e)))
            
    def iCanHazLovely(self):
        try:
            self.lovely_releases = iCanHazReleases("ethangreen-dev/lovely-injector", 10)

            items = [
                f"{r['tag_name']}{' (latest)' if i == 0 else ''}"
                for i, r in enumerate(self.lovely_releases)
            ]

            def apply():
                self.lovely_version_combo.configure(values=items)

                if items:
                    self.lovely_version_combo.current(0)
                    self.lovely_release = self.lovely_releases[0]

                self.next_btn.config(state="normal")
                self.lovely_status.config(text="")

            self.after(0, apply)

        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", str(e)))
        
    def iCanHazLayout(self):
        
        self.card = tk.Frame(self, bg="#c0c0c0", bd=2, relief="groove")
        self.card.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.card, bg="#c0c0c0", width=100)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.header_canvas = tk.Canvas(self.sidebar, highlightthickness=0, bd=0)
        self.header_canvas.pack(fill="both", expand=True)

        self.header_canvas.bind("<Configure>", self.retroslopGradient)

        self.rot_text = self.retroslopText("ezInstaller")
        self.retroslopGradient()
        
        self.right_panel = tk.Frame(self.card, bg="#c0c0c0")
        self.right_panel.pack(side="left", fill="both", expand=True)
        
        self.title_label = tk.Label(
            self.right_panel,
            text="",
            font=("Tahoma", 11, "bold"),
            bg="#c0c0c0",
            anchor="w"
        )
        self.title_label.pack(fill="x", padx=20, pady=(15, 5))
        
        self.steps_label = tk.Label(
            self.right_panel,
            text="Step 1 of 4",
            bg="#c0c0c0",
            fg="#212121",
            font=("Tahoma", 9)
        )
        self.steps_label.pack(anchor="w", padx=20)
        
        
        self.content_area = tk.Frame(self.right_panel, bg="#c0c0c0")

        self.bottom_bar = tk.Frame(self.right_panel, bg="#c0c0c0", height=50)
        self.bottom_bar.pack(side="bottom", fill="x")
        self.bottom_bar.pack_propagate(False)

        self.bottom_bar.columnconfigure(0, weight=1)
        self.bottom_bar.columnconfigure(1, weight=0)

        self.spacer = tk.Frame(self.bottom_bar, bg="#c0c0c0")
        self.spacer.grid(row=0, column=0, sticky="ew")

        self.nav_frame = tk.Frame(self.bottom_bar, bg="#C0C0C0")
        self.nav_frame.grid(row=0, column=1, sticky="e", padx=12, pady=8)


        self.content_area.pack(
            side="top",
            fill="both",
            expand=True,
            padx=20,
            pady=15
        )

        
        self.back_btn = tk.Button(
            self.nav_frame,
            text="< Back",
            width=12,
            font=self.default_font,
            state="disabled"
        )
        self.back_btn.pack(side="left", padx=5, ipady=2)

        self.next_btn = tk.Button(
            self.nav_frame,
            text="Next >",
            width=12,
            font=self.default_font
        )
        self.next_btn.pack(side="left", padx=5, ipady=2)

    def whereTheFuckAmI(self, step):
        self.steps_label.config(text=f"Step {step} of 5")

    def wizardClear(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        self.content_area.update_idletasks()
        self.content_area.update()
            

    def pageIntro(self):
        self.whereTheFuckAmI(1)
        self.wizardClear()
        self.title_label.config(text="Welcome to ezInstaller")
        tk.Label(self.content_area, text="This installer will help you install and/or update Lovely Injector and/or Steamodded.",
                 bg="#C0C0C0", font=self.default_font).pack(anchor="w", pady=15)

        self.chachaSlide(
            back_state="disabled",
            next_cmd=self.pageTOC,
            next_text="Next >"
        )
        
    def pageTOC(self):
        self.whereTheFuckAmI(2)
        self.wizardClear()

        self.title_label.config(text="Terms & License Agreement")

        container = tk.Frame(self.content_area, bg="#C0C0C0")
        container.pack(fill="both", expand=True)

        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=0)
        container.rowconfigure(2, weight=0)
        container.columnconfigure(0, weight=1)
        
        frame = tk.Frame(container, bg="#C0C0C0")
        frame.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        text = tk.Text(
            frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("MS Sans Serif", 9),
            bg="white",
            relief="sunken",
            bd=2
        )
        text.pack(fill="both", expand=True)

        scrollbar.config(command=text.yview)

        text.config(state="normal")

        license_text = textwrap.dedent("""
END USER LICENSE AGREEMENT (EULA)

This End User License Agreement (“Agreement”) is a legally binding contract between you (“User,” “You,” or “Your”) and the software developer, LasagnaFelidae
 (“Developer,” “we,” “us,” or “our”), governing Your use of the software application known as “ezInstaller” (the “Software”).

By installing, accessing, or using the Software, You expressly acknowledge that You have read, understood, and agree to be bound by the terms of this Agreement. If You do not agree to this Agreement, You must immediately cease all use of the Software and uninstall it from Your system.

1. DEFINITIONS

1.1 “Software” refers to the desktop application known as “ezInstaller,” including all associated updates, components, scripts, and documentation provided by the Developer.

1.2 “Game” refers to any third-party video game for which the Software may install or modify content.

1.3 “Mods” or “Modifications” refers to third-party modifications, files, patches, or content not originally provided by the Game’s official developers.

1.4 “Third-Party Content” refers to any Mods, repositories, files, or downloadable content sourced externally, including but not limited to content obtained via GitHub or other online services.

1.5 “User” refers to any individual or entity installing, accessing, or using the Software.

2. LICENSE GRANT

2.1 The Software is licensed under the terms of the GNU General Public License Version 3 (GPLv3).
    https://www.gnu.org/licenses/gpl-3.0.en.html

2.2 Subject to the terms of GPLv3, You are granted the freedom to:

Run the Software for any purpose;
Study how the Software works and modify it;
Redistribute copies of the Software;
Distribute modified versions of the Software.

2.3 This license explicitly permits access to source code and modification of the Software, and no provision in this Agreement shall be interpreted to restrict rights granted under GPLv3.

2.4 The full text of the GNU General Public License v3 governs in case of conflict between this Agreement and GPLv3.

3. RESTRICTIONS ON USE

You agree that You shall NOT:

3.1 You may not impose additional restrictions beyond those permitted under the GNU GPLv3.

3.2 You may not remove, alter, or obscure any copyright notices, license notices, or attribution contained within the Software.

3.3 Any redistribution of the Software or derivative works must comply with the terms of GPLv3, including the requirement to provide source code or an offer to provide source code.

4. THIRD-PARTY CONTENT DISCLAIMER

4.1 The Software may facilitate the download, installation, or modification of third-party game modifications (“Mods”) sourced from external repositories, including but not limited to:

https://github.com/Steamodded/smods
https://github.com/ethangreen-dev/lovely-injector

4.2 These Mods are independent works created and maintained by third-party authors and are not part of the Software.

4.3 The Developer does not control, verify, or guarantee the safety, legality, functionality, or integrity of any Third-Party Content.

4.4 All Mods are downloaded and installed at the User’s sole discretion and risk.

4.5 The Developer shall not be responsible for any consequences resulting from the use of Third-Party Content, including but not limited to system instability, game corruption, or security vulnerabilities.

5. NO WARRANTY

5.1 THE SOFTWARE IS PROVIDED STRICTLY ON AN “AS IS” AND “AS AVAILABLE” BASIS.

5.2 TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE DEVELOPER DISCLAIMS ALL WARRANTIES, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

5.3 THE DEVELOPER DOES NOT WARRANT THAT:

THE SOFTWARE WILL FUNCTION WITHOUT INTERRUPTION OR ERROR;
THE SOFTWARE IS FREE FROM BUGS, VIRUSES, OR DEFECTS;
ANY MODIFICATIONS MADE TO GAME FILES WILL NOT CAUSE DAMAGE OR INSTABILITY.

6. LIMITATION OF LIABILITY

6.1 TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE DEVELOPER SHALL NOT BE LIABLE FOR ANY DAMAGES WHATSOEVER ARISING OUT OF OR RELATED TO THE USE OR INABILITY TO USE THE SOFTWARE.

6.2 THIS INCLUDES, WITHOUT LIMITATION:

DIRECT, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES;
LOSS OF DATA, GAME PROGRESS, OR SAVED FILES;
GAME CRASHES, CORRUPTION, OR INSTABILITY;
ACCOUNT BANS OR RESTRICTIONS IMPOSED BY GAME DEVELOPERS OR PLATFORMS;
SECURITY BREACHES OR MALWARE INTRODUCED THROUGH THIRD-PARTY CONTENT.

6.3 THE USER EXPRESSLY ASSUMES ALL RISK ASSOCIATED WITH THE USE OF THE SOFTWARE.

7. USER RESPONSIBILITY AND RISK ACKNOWLEDGMENT

7.1 The User assumes full responsibility for all actions performed using the Software.

7.2 The User acknowledges and agrees that:

Modifying game files may violate third-party terms of service;
Such actions may result in bans or restrictions;
Game data may become corrupted or unusable;
The Developer bears no responsibility for such outcomes.

7.3 All risks associated with the use of Mods and file modifications are assumed entirely by the User.

8. INDEMNIFICATION

8.1 The User agrees to indemnify and hold harmless the Developer from any claims, damages, liabilities, costs, or expenses arising from:

Use or misuse of the Software;
Use of Third-Party Content;
Distribution of modified versions of the Software;
Violation of applicable laws or third-party terms.

9. THIRD-PARTY AUTHORS DISCLAIMER

9.1 Mod authors and third-party content creators are independent contributors and are not affiliated with the Developer.

9.2 The Developer makes no representations or warranties regarding Third-Party Content.

9.3 Any issues related to Mods must be directed to their respective authors.

10. TERMINATION

10.1 This Agreement terminates automatically if You fail to comply with GPLv3 or this Agreement.

10.2 Upon termination, You may continue using and redistributing the Software only as permitted under GPLv3.

11. GOVERNING LICENSE

11.1 This Software is licensed under GPLv3.

11.2 Nothing in this Agreement shall restrict or supersede rights granted under GPLv3.

11.3 In case of conflict, GPLv3 shall govern exclusively.

12. DATA AND INTERNET USAGE

12.1 The Software may access external internet resources to retrieve Mod files and updates.

12.2 These external sources are not controlled by the Developer.

12.3 The User acknowledges that downloaded content may change, become unavailable, or contain unintended risks.

13. ACCEPTANCE OF TERMS

13.1 By installing, using, modifying, or distributing the Software, You confirm that You have read and agree to this Agreement and the GPLv3 license.

13.2 If You do not agree, You must immediately cease use of the Software and remove all copies from Your system.

        
THIRD-PARTY LICENSES
────────────────────────────
        """)

        text.insert("1.0", license_text + "\n")

        text.insert("end", "Lovely Injector\n")
        text.insert("end", "© Ethan Green\n")
        text.insert("end", "- MIT License (click to view)\n", "lovely_link")
        text.insert("end", "\n")

        text.insert("end", "Steamodded\n")
        text.insert("end", "© Steamodded Contributors\n")
        text.insert("end", "- GPL 3.0 License (click to view)\n", "smods_link")
        text.insert("end", "\n")

        text.insert("end", "ezInstaller\n")
        text.insert("end", "© LasagnaFelidae\n")
        text.insert("end", "- GPL 3.0 License (click to view)\n", "installer_link")
        text.insert("end", "\n")

        text.tag_config("lovely_link", foreground="blue", underline=1)
        text.tag_config("smods_link", foreground="blue", underline=1)
        text.tag_config("installer_link", foreground="blue", underline=1)

        text.tag_bind("lovely_link", "<Button-1>", lambda e: self.iCanHazLicense(
            "https://opensource.org/licenses/MIT"
        ))

        text.tag_bind("smods_link", "<Button-1>", lambda e: self.iCanHazLicense(
            "https://www.gnu.org/licenses/gpl-3.0.en.html"
        ))

        text.tag_bind("installer_link", "<Button-1>", lambda e: self.iCanHazLicense(
            "https://www.gnu.org/licenses/gpl-3.0.en.html"
        ))
        
        text.config(state="disabled")

        self.agree_var = tk.BooleanVar()

        checkbox_frame = tk.Frame(container, bg="#C0C0C0")
        checkbox_frame.grid(row=1, column=0, sticky="w", pady=8)

        tk.Checkbutton(
            checkbox_frame,
            text="I accept the terms and license agreement",
            variable=self.agree_var,
            bg="#C0C0C0",
            font=self.default_font,
            command=self.termsNavToggle
        ).pack(anchor="w")
        
        self.chachaSlide(
            back_cmd=self.pageIntro,
            next_cmd=self.pageInstallSel,
            next_text="Continue",
            next_state="disabled"
        )
        
        
    def termsNavToggle(self):
        self.next_btn.config(state="normal" if self.agree_var.get() else "disabled")

    def pageInstallSel(self):
        self.whereTheFuckAmI(3)
        self.wizardClear()
        self.title_label.config(text="Choose Installation Option")

        self.choice_var = tk.IntVar(value=3)
        for text, val in [("Lovely Injector only", 1), ("Steamodded only", 2), ("Both Lovely + Steamodded", 3)]:
            tk.Radiobutton(self.content_area, text=text, variable=self.choice_var, value=val,
                          bg="#C0C0C0", font=self.default_font, anchor="w").pack(anchor="w", pady=8, padx=30)

        self.chachaSlide(
            back_cmd=self.pageIntro,
            next_cmd=self.whereAreYouGoing
        )
    def isAnyoneThere(self):
        try:
            requests.get("https://github.com", timeout=3)
            return True
        except requests.RequestException:
            return False
        
    def whereAreYouGoing(self):
        self.choice = self.choice_var.get()

        if not self.isAnyoneThere():
            messagebox.showerror(
                "No Internet Connection",
                "This installer requires an internet connection to download mods.\n\nPlease connect and try again."
            )
            return

        if self.choice in [1, 3]:
            self.pageLovely()
        else:
            self.pageSmods()
            
    def chachaSlide(self, back_cmd=None, next_cmd=None,
            back_text="< Back", next_text="Next >",
            back_state="normal", next_state="normal"):

        self.back_btn.config(
            text=back_text,
            command=back_cmd if back_cmd else lambda: None,
            state=back_state
        )

        self.next_btn.config(
            text=next_text,
            command=next_cmd if next_cmd else lambda: None,
            state=next_state
        )

    
    def pageLovely(self):
        self.whereTheFuckAmI(3)
        self.wizardClear()
        self.title_label.config(text="Select Lovely Injector Version")
        
        tk.Label(
            self.content_area,
            text="Lovely Injector requires you to install to the directory where your Balatro.exe is.\nIt selects your Steam directory by default, if it is somewhere else, please select it.",
            bg="#C0C0C0",
            fg="#404040",
            font=("MS Sans Serif", 9),
            wraplength=520,
            justify="left"
        ).pack(anchor="w", pady=(5, 10))
        
        dir_frame = tk.LabelFrame(
            self.content_area,
            text=" Balatro Directory ",
            bg="#C0C0C0",
            font=("MS Sans Serif", 9, "bold"),
            padx=12,
            pady=12
        )
        dir_frame.pack(fill="x", pady=10)

        inner = tk.Frame(dir_frame, bg="#C0C0C0")
        inner.pack(fill="x")

        entry = tk.Entry(
            inner,
            textvariable=self.game_dir_var,
            font=("Consolas", 9),
            relief="sunken",
            bd=2
        )
        entry.pack(side="left", fill="x", expand=True, ipady=3)

        tk.Button(
            inner,
            text="Browse...",
            width=12,
            font=self.default_font,
            command=self.whereIsBalatro
        ).pack(side="left", padx=(10, 0))

        version_row = tk.Frame(self.content_area, bg="#C0C0C0")
        version_row.pack(anchor="w", pady=(18, 8))

        tk.Label(
            version_row,
            text="Select Version:",
            bg="#C0C0C0",
            font=self.default_font
        ).pack(side="left", padx=(0, 10))

        self.lovely_version_combo = ttk.Combobox(
            version_row,
            state="readonly",
            font=self.default_font,
            width=28
        )
        self.lovely_version_combo.pack(side="left")

        self.lovely_version_combo.bind("<<ComboboxSelected>>", self.letmegetthatInjector)

        self.lovely_status = tk.Label(
            self.content_area,
            text="Fetching available versions...",
            bg="#C0C0C0",
            fg="#6A6A6A",
            font=("MS Sans Serif", 8)
        )
        self.lovely_status.pack(anchor="w", padx=4, pady=(0, 12))

        threading.Thread(target=self.iCanHazLovely, daemon=True).start()

        next_label = "Install" if self.choice == 1 else "Next >"

        self.chachaSlide(
            back_cmd=self.pageInstallSel,
            next_cmd=self.whereAreYouGoing2,
            next_text=next_label,
            next_state="disabled"
        )
        
    def whereAreYouGoing2(self):
        if self.choice in [2, 3]:
            self.pageSmods()
        else:
            self.versionCheck()
    
    def pageSmods(self):
        self.whereTheFuckAmI(3)
        self.wizardClear()
        self.title_label.config(text="Select Steamodded Version")
        tk.Label(
            self.content_area,
            text="Changing this folder will create a symlink to the new Mods directory.",
            bg="#C0C0C0",
            fg="#404040",
            font=("MS Sans Serif", 9),
            wraplength=520,
            justify="left"
        ).pack(anchor="w", pady=(5, 10))

        dir_outer = tk.LabelFrame(
            self.content_area,
            text=" Installation Directory ",
            bg="#C0C0C0",
            font=("MS Sans Serif", 9, "bold"),
            padx=12,
            pady=12
        )
        dir_outer.pack(fill="x", pady=(10, 18))

        dir_inner = tk.Frame(dir_outer, bg="#C0C0C0")
        dir_inner.pack(fill="x")

        self.dir_var = tk.StringVar(value=str(self.mods_base))

        dir_entry = tk.Entry(
            dir_inner,
            textvariable=self.dir_var,
            font=("Consolas", 9),
            relief="sunken",
            bd=2,
            state="readonly"
        )
        dir_entry.pack(side="left", fill="x", expand=True, ipady=3)

        browse_btn = tk.Button(
            dir_inner,
            text="Browse...",
            width=12,
            font=self.default_font,
            command=self.caniMoveThisOverHere
        )
        browse_btn.pack(side="left", padx=(10, 0))

        version_row = tk.Frame(self.content_area, bg="#C0C0C0")
        version_row.pack(anchor="w", pady=(18, 8))

        tk.Label(
            version_row,
            text="Select Version:",
            bg="#C0C0C0",
            font=self.default_font
        ).pack(side="left", padx=(0, 10))

        self.version_combo = ttk.Combobox(
            version_row,
            state="readonly",
            font=self.default_font,
            width=28
        )
        self.version_combo.pack(side="left")

        self.version_combo.bind("<<ComboboxSelected>>", self.letmegetthatSmods)

        self.status = tk.Label(
            self.content_area,
            text="Fetching available versions...",
            bg="#C0C0C0",
            fg="#6A6A6A",
            font=("MS Sans Serif", 8)
        )
        self.status.pack(anchor="w", padx=4, pady=(0, 12))

        threading.Thread(target=self.iCanHazSmods, daemon=True).start()
        
        self.chachaSlide(
            back_cmd=self.pageInstallSel,
            next_cmd=self.versionCheck,
            next_text="Install",
            next_state="disabled"
        )

    def versionCheck(self):
        if self.choice in [2, 3] and not self.selected_release:
            messagebox.showwarning("Warning", "Please select a Steamodded version")
            return

        if self.choice in [1, 3] and not self.lovely_release:
            messagebox.showwarning("Warning", "Please select a Lovely version")
            return

        self.pageInstalling()

    def pageInstalling(self):
        self.whereTheFuckAmI(4)
        self.wizardClear()
        container = tk.Frame(self.content_area, bg="#C0C0C0")
        container.pack(fill="both", expand=True)

        self.progress_label = tk.Label(
            container,
            text="Starting installation...\nPlease wait.",
            bg="#C0C0C0",
            font=("MS Sans Serif", 11)
        )
        self.progress_label.pack(anchor="w", pady=(0, 5))

        log_frame = tk.Frame(container, bg="#C0C0C0")
        log_frame.pack(fill="both", expand=True)

        self.log_box = tk.Text(
            log_frame,
            bg="#0f0f0f",
            fg="white",
            font=("Consolas", 9),
            relief="sunken",
            bd=2,
            insertbackground="white"
        )
        self.log_box.config(state="disabled")
        self.log_box.pack(side="left", fill="both", expand=True)

        self.log_box.tag_config("info", foreground="#00bfff")
        self.log_box.tag_config("success", foreground="#00ff7f")
        self.log_box.tag_config("warning", foreground="#ffd700")
        self.log_box.tag_config("error", foreground="#ff4d4d")
        self.log_box.tag_config("step", foreground="#ffffff", font=("Consolas", 9, "bold"))
        self.log_box.tag_config("system", foreground="#c0c0c0")

        scroll = tk.Scrollbar(log_frame, command=self.log_box.yview)
        scroll.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scroll.set)

        threading.Thread(target=self.installConsole, daemon=True).start()
        
        self.chachaSlide(
            back_state="disabled",
            next_state="disabled"
        )
        self.next_btn.config(state="disabled")
        self.back_btn.config(state="disabled")

    def installConsole(self):
        if self.installing:
            return
        self.after(0, lambda: self.next_btn.config(state="disabled"))
        self.after(0, lambda: self.back_btn.config(state="disabled"))
        self.installing = True

        
        
        sys.stdout = Installer.TextRedirector(self.log_box)
        sys.stderr = Installer.TextRedirector(self.log_box)

        try:
            print("STEP: Checking game state")
            if balala():
                print("WARNING: Balatro is currently running")
                self.canYouCloseTheDamnGameYet()

            print("SUCCESS: Game is closed")

            if self.choice in [1, 3]:
                print("STEP: Installing Lovely Injector")
                print("INFO: Fetching latest release metadata")

                release = self.lovely_release or iCanHazReleases(
                    "ethangreen-dev/lovely-injector"
                )[0]

                print(f"INFO: Selected version {release['tag_name']}")
                print("INFO: Downloading archive...")

                target = self.balatro_dir or Path(".")
                iCanHazDLnUnzip(release, target)

                print("SUCCESS: Lovely Injector installed")
                time.sleep(2)

            if self.choice in [2, 3]:
                print("STEP: Installing Steamodded")
                print("INFO: Fetching latest release metadata")
                
                smods_release = self.selected_release or iCanHazReleases(
                    "Steamodded/smods"
                )[0]

                print(f"INFO: Selected version {smods_release['tag_name']}")
                time.sleep(1)
                print("INFO: Removing existing SMODS directories...")
                for item in self.mods_base.iterdir():
                    if item.is_dir() and item.name.lower().startswith("smods-"):
                        shutil.rmtree(item, ignore_errors=True)
                        print(f"SUCCESS: Removed {item}" )
                        time.sleep(1)


                print("INFO: Downloading archive...")
                versioned_name = f"smods-{self.selected_release['tag_name']}"
                iCanHazDLnUnzip(self.selected_release, self.mods_base, versioned_name)
                
                print("SUCCESS: Steamodded installed")
                time.sleep(2)

            self.after(0, self.pageCompleted)

        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", str(e)))
    
    def pageCompleted(self):
        self.whereTheFuckAmI(5)
        self.wizardClear()

        self.title_label.config(text="Installation Complete")

        choice = getattr(self, "install_choice", self.choice)
        release = getattr(self, "install_release", self.selected_release)
        balatro_dir = getattr(self, "install_balatro_dir", self.balatro_dir)
        mods_base = getattr(self, "install_mods_base", self.mods_base)

        root = tk.Frame(self.content_area, bg="#C0C0C0")
        root.pack(fill="both", expand=True)
        
        tk.Label(
            root,
            text=(
                "Thank you for using ezInstaller!\n\n"
                "Mods can safely now be installed to the same \"Mods\" directory \nwhere Steamodded has been installed."
            ),
            bg="#C0C0C0",
            font=("MS Sans Serif", 10),
            justify="left",
            anchor="w",
            wraplength=520
        ).pack(anchor="w", fill="x", expand=True, padx=10, pady=(10, 15))

        locations = tk.LabelFrame(
            root,
            text=" Installed Components ",
            bg="#C0C0C0",
            font=("MS Sans Serif", 9, "bold"),
            padx=10,
            pady=10
        )
        locations.pack(fill="x", expand=False, padx=30, pady=(10, 5))
        
        options_frame = tk.Frame(root, bg="#C0C0C0")
        options_frame.pack(fill="x", padx=30, pady=(5, 15))

        if not hasattr(self, "launch_var"):
            self.launch_var = tk.BooleanVar(value=True)

        tk.Checkbutton(
            options_frame,
            text="Launch Balatro",
            variable=self.launch_var,
            bg="#C0C0C0",
            font=self.default_font,
            activebackground="#C0C0C0"
        ).pack(anchor="w")

        if choice in [1, 3] and balatro_dir:
            frame = tk.Frame(locations, bg="#C0C0C0")
            frame.pack(fill="x", pady=4)

            tk.Label(
                frame,
                text="Lovely:",
                width=8,
                anchor="w",
                bg="#C0C0C0",
                font=("MS Sans Serif", 9, "bold")
            ).pack(side="left")

            tk.Label(
                frame,
                text=str(balatro_dir),
                anchor="w",
                bg="white",
                relief="sunken", 
                bd=1,
                font=("Consolas", 8)
            ).pack(side="left", fill="x", expand=True)

        if choice in [2, 3] and release:
            frame = tk.Frame(locations, bg="#C0C0C0")
            frame.pack(fill="x", pady=4)

            tag = release.get("tag_name", "unknown")
            smods_path = str(mods_base / f"smods-{tag}")

            tk.Label(
                frame,
                text="SMODS:",
                width=8,
                anchor="w",
                bg="#C0C0C0",
                font=("MS Sans Serif", 9, "bold")
            ).pack(side="left")

            tk.Label(
                frame,
                text=smods_path,
                anchor="w",
                bg="white",
                relief="sunken", 
                bd=1,
                font=("Consolas", 8)
            ).pack(side="left", fill="x", expand=True)
            

        self.chachaSlide(
            back_state="disabled",
            next_text="Finish",
            next_cmd=self.finish_installer
        )
        
    
    

    class TextRedirector:
        def __init__(self, widget):
            self.widget = widget

        def write(self, message):
            msg = message.strip()
            if not msg:
                return

            tag = "info"

            upper = msg.upper()
            if "ERROR" in upper:
                tag = "error"
            elif "WARNING" in upper:
                tag = "warning"
            elif "SUCCESS" in upper:
                tag = "success"
            elif "STEP" in upper:
                tag = "step"
            elif "LOADING" in upper or "INSTALL" in upper:
                tag = "system"

            import time
            timestamp = time.strftime("%H:%M:%S")

            formatted = f"[{timestamp}] {msg}\n"

            self.widget.after(
                0,
                self._write,
                formatted,
                tag
            )

        def _write(self, msg, tag):
            self.widget.config(state="normal")
            self.widget.insert("end", msg, tag)
            self.widget.see("end")
            self.widget.config(state="disabled")

        def flush(self):
            pass
        
        
if __name__ == "__main__":
    app = Installer()
    app.mainloop()