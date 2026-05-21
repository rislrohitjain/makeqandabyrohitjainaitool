# 🚀 MakeQandA Assessment Engine - Postman Integration Guide

This directory contains resources for developers and QA engineers to test and integrate the REST API of the **Automated Rohit Jain's Question Paper & Answer Key Assessment Engine** in their mobile or web application workflows.

---

## 📂 Shareable Artifacts Included

1. **`makeqanda_api_collection.json`**: The complete API endpoints suite containing form parameter keys, validation boundaries, and folder groupings.
2. **`local_environment.json`**: A preconfigured Postman Environment file mapping the global `{{base_url}}` variable to the default server host `http://127.0.0.1:8000`.

---

## 🛠️ Step-by-Step Integration

### Step 1: Launch the REST API Server
From the project root directory, run the batch script:
```powershell
run_api.bat
```
* The FastAPI server will boot on port `8000` locally.
* You can verify the API is running by visiting the interactive Swagger docs at **`http://127.0.0.1:8000/docs`**.

### Step 2: Import Files to Postman
1. Open your **Postman** application.
2. Click on the **Import** button in the top left corner of the Postman interface.
3. Select and drag-and-drop both **`makeqanda_api_collection.json`** and **`local_environment.json`** into the upload dialog.
4. Click **Import** to load them.

### Step 3: Select the Local Environment
1. In the top-right corner of Postman, locate the Environment dropdown selector (it usually defaults to "No Environment").
2. Select **"Local MakeQandA Environment"** from the dropdown list. This resolves the `{{base_url}}` placeholder in all requests to point to your local backend server.

### Step 4: Testing the Endpoints
* **Get Developer Profile**: Hit this request (`GET`) to instantly fetch Rohit Jain's credentials (Sr. Software Engineer, BCA, MCA) and portfolio URLs.
* **Submit Q&A Generation (Asynchronous)**:
  1. Open the request `POST Submit Q&A Generation (Asynchronous)`.
  2. Select the **Body** tab and choose **form-data**.
  3. Under the `files` key, hover over the value field, click the file selection dialog, and upload up to 5 source documents (`.pdf`, `.docx`, `.txt`).
  4. Send the request. Note the returned `session_id`.
* **Check Session Status**:
  1. Open the `Check Session Status & Telemetry` request.
  2. Under the **Params** tab, replace the `session_id` path variable with the 8-character ID returned from the generation submission.
  3. Hit Send to inspect the real-time agent processing stream.
* **Download Output File**:
  1. Locate the download endpoint.
  2. Input the `mobile_number`, `session_id`, and `filename` parameters.
  3. Download the zipped package (password encrypted using the mobile number PIN), standard Excel sheets, or separate question paper PDFs.
