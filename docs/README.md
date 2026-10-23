# MedNova documentation index

Use the root [README](../README.md) and [VS Code run guide](../OPEN_IN_VSCODE.md) for the current entry points. Older reports are retained as dated audit evidence, not competing setup instructions.

## Current operational guides

- [Cleanup report and recovery point](CLEANUP_REPORT.md)
- [MySQL operations](MYSQL_OPERATIONS.md), [database viewer](VSCODE_DATABASE.md), [database engine configuration](DATABASE_SETUP.md)
- [Patient assistant and persistent staff handoff](PATIENT_ASSISTANT_REPORT.md), [intent catalogue](PATIENT_ASSISTANT_INTENTS.md)
- [Scheduling, admissions and pharmacy upgrade](HOSPITAL_UPGRADE_REPORT.md)
- [Email/payment/video/storage integrations](INTEGRATIONS.md), [deployment target requirements](VERCEL_DEPLOYMENT.md)

## Historical checkpoints and design

- [Initial repair](REPAIR_AND_VERCEL_REPORT.md), [initial test report](TEST_REPORT.md), [security review](SECURITY_REVIEW.md)
- [UI redesign](UI_REDESIGN_REPORT.md), [product expansion](PRODUCT_IMPLEMENTATION_REPORT.md), [system audit](FINAL_SYSTEM_REPORT.md)
- [Figma/PostgreSQL transformation](PRODUCT_TRANSFORMATION_REPORT.md), [source-folder delivery](LOGIN_AND_FOLDER_DELIVERY.md)
- [First chatbot checkpoint](CHATBOT_IMPLEMENTATION.md)

`design/` and `docs/design/` contain editable construction sources, tokens, screenshots and design verification. They are distinct from runtime assets and remain useful project records.

## Raw verification

The `verification/` directory preserves distinct tests, route matrices, schema metadata and screenshots. [Identical historical output aliases](verification/EVIDENCE_INDEX.md) identify the few consolidated copies without erasing checkpoint/environment associations. MySQL and PostgreSQL outputs remain separate even when their bytes match. New cleanup results are named `cleanup-*`; older pass counts are not rewritten as current results.
