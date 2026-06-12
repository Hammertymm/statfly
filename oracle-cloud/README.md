# Fly Intelligence Platform — Oracle Cloud (Always Free)

Deploy 24/7 on Oracle Cloud **$0/month** using an Ampere A1 VM.

## Part 1 — Create Oracle account & VM (~15 min)

### 1. Sign up

1. Go to [oracle.com/cloud/free](https://www.oracle.com/cloud/free/)
2. Create account (credit/debit card required for verification — temporary hold only, not charged if you stay in Always Free)
3. Choose **home region** carefully (e.g. Sydney if you're in Australia, or closest to you)

### 2. Create the VM

1. Oracle Console → **Compute** → **Instances** → **Create instance**
2. Name: `fly-intelligence`
3. **Image:** Ubuntu 24.04 (aarch64)
4. **Shape:** Ampere → `VM.Standard.A1.Flex`
   - **1 OCPU**, **6 GB RAM** (plenty; 2 GB also works)
5. **Networking:** use default VCN
6. **Add SSH keys:** download private key or paste your public key
7. **Boot volume:** 50 GB (default is fine)
8. Click **Create**

If you get **Out of host capacity**: try a different availability domain, retry later, or start with 1 OCPU / 2 GB in another region.

### 3. Open firewall port 8787

**Oracle Security List (required):**

1. **Networking** → **Virtual cloud networks** → your VCN
2. Click the **Subnet** → **Default Security List**
3. **Add Ingress Rules:**
   - Source CIDR: `0.0.0.0/0` (or your home IP `/32` for security)
   - IP Protocol: TCP
   - Destination port: `8787`
   - Description: Fly Intelligence dashboard

### 4. SSH into the VM

```powershell
# Windows — use the private key Oracle gave you
ssh -i C:\path\to\your-key.key ubuntu@YOUR_PUBLIC_IP
```

---

## Part 2 — Install platform on VM (~5 min)

On the VM:

```bash
git clone https://github.com/Hammertymm/scorefly.git ~/scorefly
cd ~/scorefly
bash oracle-cloud/setup-vm.sh
```

Or use the Oracle compose file directly:

```bash
sudo mkdir -p /data/flytime/exports
sudo chown ubuntu:ubuntu /data/flytime -R
cd ~/scorefly
docker compose -f docker-compose.oracle.yml up -d --build
docker compose -f docker-compose.oracle.yml exec fly-intelligence python main.py init
```

Note the **public IP** from the Oracle instance page.

Test: `http://YOUR_PUBLIC_IP:8787/api/health`

---

## Part 3 — Upload your local database (one time)

Your laptop has ~30k matches in SQLite. Upload from Windows:

```powershell
cd C:\Projects\ScoreFly\scorefly\oracle-cloud
.\upload-db.ps1 -VmIp YOUR_PUBLIC_IP -KeyPath C:\path\to\your-key.key
```

Manual alternative:

```powershell
scp -i C:\path\to\key.key `
  C:\Projects\ScoreFly\scorefly\flytime-engine\data\flytime_engine.db `
  ubuntu@YOUR_PUBLIC_IP:/data/flytime/flytime_engine.db

ssh -i C:\path\to\key.key ubuntu@YOUR_PUBLIC_IP "cd ~/scorefly && docker compose -f docker-compose.oracle.yml restart"
```

---

## Part 4 — Verify

| Check | URL |
|-------|-----|
| Dashboard | `http://YOUR_PUBLIC_IP:8787/` |
| Health | `http://YOUR_PUBLIC_IP:8787/api/health` |
| Live matches | `http://YOUR_PUBLIC_IP:8787/api/live` |

Confirm `status: running` and `last_poll_at` updates every ~12 seconds.

---

## Maintenance

```bash
# SSH to VM
cd ~/scorefly
docker compose -f docker-compose.oracle.yml logs -f          # view logs
docker compose -f docker-compose.oracle.yml restart          # restart
docker compose -f docker-compose.oracle.yml pull && docker compose -f docker-compose.oracle.yml up -d --build  # update
cp /data/flytime/flytime_engine.db /data/flytime/backup-$(date +%Y%m%d).db  # backup
```

---

## Cost

| Item | Cost |
|------|------|
| Ampere A1 Always Free VM | $0 |
| ESPN API | $0 |
| Egress (10 TB/month free) | $0 for dashboard use |
| **Total** | **$0/month** |

Stay within Always Free shapes only. Do not upgrade to Pay As You Go paid instances.

---

## Local machine

Local autostart has been removed. Your laptop no longer runs the collector.

Optional — remove local DB after confirming cloud works:

```powershell
Remove-Item C:\Projects\ScoreFly\scorefly\flytime-engine\data\flytime_engine.db -ErrorAction SilentlyContinue
```

Keep a backup until cloud is verified.
