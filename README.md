# 3DGS Batch Processor 🚀
<img width="1156" height="1244" alt="grafik" src="https://github.com/user-attachments/assets/3f42fa8f-8a05-4382-b6c5-0802d726f6db" />

A lightweight, multi-threaded Windows GUI tool to batch-process 3D Gaussian Splatting (`.ply`) frame sequences. 

Perfect for ComfyUI / Apple SHARP 4DGS workflows! It automatically crops, transforms, and compresses massive raw frame sequences into web-ready `.spz` (or cleaned `.ply`) files with a single click.

![3DGS Batch Processor UI](https://via.placeholder.com/800x450.png?text=Add+a+Screenshot+of+your+UI+here) *(Note: Add a screenshot of your tool to your repo and replace this link!)*

## ✨ Key Features
* **⚡ Multi-Threaded Processing:** Utilizes your CPU's multi-core architecture to process multiple frames concurrently. What used to take minutes now takes seconds!
* **🎯 SuperSplat Coordinate Fix:** Automatically inverts X/Y translations and handles bounding box math under the hood. You can copy your crop and translation values directly from [PlayCanvas SuperSplat](https://playcanvas.com/supersplat) without altering the signs!
* **📦 Smart Zero-Padding (`_0001`):** Renames messy file sequences automatically into strictly formatted 4-digit sequences (e.g., `animation_0001.spz`), ensuring 100% compatibility with 4DGS web players.
* **🧪 Create Testfile:** Process only the 1st frame of your stack to quickly verify your cropbox and rotation values before rendering the entire sequence.
* **💾 Persistent Settings:** The tool remembers your inputs and automatically saves them for your next session.
* **🗜️ Ultra Compression:** Converts heavy `.ply` point clouds to the highly efficient Niantic `.spz` format (using `gsbox`), reducing file sizes by up to 90% without losing visual fidelity.
* **🖱️ Workflow Integration:** Use the built-in folder browser, or set it up in your Windows "Send To" context menu for instant right-click processing!

## 📥 Download & Usage (For Windows Users)

You don't need to install Python. Just download the standalone executable:

1. Go to the **[Releases](../../releases)** page and download `3DGS_Batch_processor.exe`.
2. **Double-click** the `.exe` to open the GUI and browse for your folder containing `.ply` frames.
3. **(Optional Pro-Tip) Context Menu Setup:** 
   * Create a shortcut of the `.exe`. 
   * Press `Win + R`, type `shell:sendto`, and hit Enter. 
   * Move the shortcut into this hidden folder. Now you can right-click any folder or selected `.ply` files -> *Send To* -> *3DGS Batch Processor*!

## 🛠️ Step-by-Step Workflow

1. Open a single raw `.ply` frame in **[PlayCanvas SuperSplat](https://playcanvas.com/supersplat)**.
2. Align the model (Translation/Rotation) and draw a Bounding Box around the area you want to keep.
3. Copy those exact values into the **3DGS Batch Processor**.
4. (Optional) Click **Create Testfile (1st)** to render a single `_TEST` file and check if everything looks perfect.
5. Choose a filename prefix, select `.spz` or `.ply`, and click **Process All Files**.
6. Find your cleaned, aligned, and sequentially numbered sequence in the newly created `output_spz` folder!

## 💻 Building from Source (For Developers)

If you want to modify the Python code or build the `.exe` yourself:

1. **Prerequisites:** 
   * Install Python 3.8+
   * Install requirements: `pip install plyfile pyinstaller`
   * Download the latest Windows release of [gsbox](https://github.com/gotoeasy/gsbox/releases) and place `gsbox.exe` in the same directory as the script.
2. **Run as script:**
  
   `python 3dgs_batch_processor.py`
   
    Compile to Standalone .exe:
   `pyinstaller --noconsole --onefile --add-binary "gsbox.exe;." 3dgs_batch_processor.py`

    The compiled file will be located in the dist/ folder and already contains gsbox natively!

🤝 Credits & Under the Hood

    Usesgsbox (written in Go) for lightning-fast transformation and SPZ conversion.

    Uses plyfile for safe spherical harmonics retention during the auto-cropping phase.

    Built to optimize ComfyUI / Apple SHARP sequence outputs for the web.
