
# 🚗 Parking Ticket Automation System

This project automates the handling of parking/traffic tickets for rental companies using a fully serverless AWS-based pipeline. It integrates OCR, AI, and email notifications to eliminate manual ticket processing.

![Architecture Diagram](project_diagram.png)

---

## 🔧 Key Technologies

- **Frontend**: HTML/CSS/JS dashboard (hosted on S3)
- **AWS Services**:
  - S3 (image storage)
  - Lambda (4 functions)
  - API Gateway (HTTP API for `/upload` and `/tickets`)
  - DynamoDB (`Tickets` and `Drivers` tables)
  - SES (driver/admin notifications)
- **External APIs**:
  - Google Cloud Vision (OCR)
  - Gemini 1.5 Flash (AI parsing)
- **IaC**: Terraform (provision Lambda + API Gateway)

---

## ⚙️ Project Workflow

1. **Admin uploads a ticket image** via `dashboard.html`.
2. The image is sent to API Gateway and stored in S3.
3. S3 triggers a Lambda (`OcrToAWS`) that calls Google Vision OCR.
4. OCR text is passed to `ProcessTicketOCR`, which:
   - Uses Gemini to extract fields
   - Stores the result in DynamoDB
   - Looks up the driver by licence plate
   - Sends an email with a proof of payment link or fallback to admin
5. Admins can view all `PENDING` tickets on the dashboard (via `/tickets` endpoint).

---

## 🗂️ Folder Structure

```
lambda_google_ocr/
├── lambdas/
│   ├── upload_to_s3/
│   ├── ocr_to_aws/
│   ├── process_ticket/
│   └── list_tickets/
├── terraform/
│   ├── main.tf
│   └── lambda zip files
├── frontend/
│   ├── dashboard.html
│   └── index.html
├── test_assets/
│   └── test_ticket.jpg
├── project_diagram.png
├── .gitignore
└── README.md
```

---

## 📦 Deployment Steps

1. `terraform init && terraform apply` to deploy `ListTickets` + API
2. Zip and upload each Lambda manually or via CI
3. Deploy frontend to S3 (static site)
4. Set proper CORS in API Gateway (`POST` and `GET` support)
5. Set environment variables for:
   - `EMAIL_FROM_ADDRESS`
   - `PAYMENT_FORM_URL`
   - `GEMINI_API_KEY`

---

## ✨ Highlighted Skills

✅ Serverless architecture  
✅ Multi-cloud integration (AWS + Google)  
✅ Real-time OCR and AI parsing  
✅ Automated email workflows  
✅ Dashboard UI with secure fetch  
✅ Terraform IaC  
✅ Full-stack pipeline with monitoring

---

## 🧠 Future Improvements

- Mark tickets as paid from dashboard
- Admin authentication (Cognito)
- Search/filter ticket list
- Upload PDF/ticket multipage support

---



## 📄 License

MIT – Free to use and adapt.
