const fs = require('fs');

// 1. Fix screening_service.py
let sc = fs.readFileSync('backend/app/services/screening_service.py', 'utf8');
sc = sc.replace(/\r\n/g, '\n');

const scTarget = `        # Target recipient email for notifications
        target_email = getattr(request, "notification_email", None)
        if target_email:
            target_email = target_email.strip()
        if not target_email:
            target_email = settings.email_to`;

const scReplacement = `        # Target recipient email for notifications - strictly only what is given as input
        target_email = getattr(request, "notification_email", None)
        if target_email and target_email.strip():
            target_email = target_email.strip()
        else:
            target_email = None`;

if (sc.includes(scTarget)) {
  sc = sc.replace(scTarget, scReplacement);
  fs.writeFileSync('backend/app/services/screening_service.py', sc, 'utf8');
  console.log('SUCCESS: Updated screening_service.py target_email');
} else {
  console.log('WARNING: scTarget not found');
}

// 2. Fix notification_service.py
let ns = fs.readFileSync('backend/app/services/notification_service.py', 'utf8');
ns = ns.replace(/\r\n/g, '\n');

const nsTarget = `    def _send_email(
        self,
        subject: str,
        html_body: str,
        attachment_bytes: Optional[bytes] = None,
        attachment_name: Optional[str] = None,
        target_email: Optional[str] = None,
    ):
        """Send email via SMTP, or save to disk if unconfigured."""
        raw_str = (target_email.strip() if target_email else None) or settings.email_to.strip()
        recipients = [r.strip() for r in raw_str.replace(";", ",").split(",") if r.strip()]`;

const nsReplacement = `    def _send_email(
        self,
        subject: str,
        html_body: str,
        attachment_bytes: Optional[bytes] = None,
        attachment_name: Optional[str] = None,
        target_email: Optional[str] = None,
    ):
        """Send email via SMTP, strictly only to input recipients."""
        # Strictly accept ONLY what is explicitly given as input (no fallbacks or hidden emails)
        raw_str = (target_email or "").strip()
        recipients = [r.strip() for r in raw_str.replace(";", ",").split(",") if r.strip()]

        if not recipients:
            # If no recipient was provided in input, do NOT send live emails to anyone!
            self._save_to_disk(subject, html_body, attachment_bytes, attachment_name)
            logger.provider_info("NOTIFY", f"Archived email to disk (no recipient input provided; live dispatch skipped).")
            return`;

if (ns.includes(nsTarget)) {
  ns = ns.replace(nsTarget, nsReplacement);
  fs.writeFileSync('backend/app/services/notification_service.py', ns, 'utf8');
  console.log('SUCCESS: Updated notification_service.py _send_email');
} else {
  console.log('WARNING: nsTarget not found');
}

// 3. Fix ScheduleConfigCard.jsx placeholder
let scc = fs.readFileSync('frontend/src/components/schedule/ScheduleConfigCard.jsx', 'utf8');
scc = scc.replace(/\r\n/g, '\n');

const sccTarget = `placeholder="e.g. prabhas.muthyala@zeniusit.com, manoj@zeniusit.com"`;
const sccReplacement = `placeholder="e.g. your.email@company.com"`;

if (scc.includes(sccTarget)) {
  scc = scc.replace(sccTarget, sccReplacement);
  fs.writeFileSync('frontend/src/components/schedule/ScheduleConfigCard.jsx', scc, 'utf8');
  console.log('SUCCESS: Updated ScheduleConfigCard.jsx placeholder');
} else {
  console.log('WARNING: sccTarget not found');
}

