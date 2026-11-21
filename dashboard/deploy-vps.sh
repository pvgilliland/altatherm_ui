#!/usr/bin/env bash
set -euo pipefail

cd /home/deploy/altathermapp
files=/home/deploy/altatherm-dashboard-deploy
web=/var/www/altathermapp/oven-dashboard
base_image=altatherm-backend:v2-oven-jobs
image=altatherm-backend:v2-oven-dashboard

test -f "$files/dist/index.html"
test -f "$files/oven_api.py"
if [ -e "$web" ]; then
    echo "Dashboard directory already exists. Check the existing deployment before replacing it."
    exit 1
fi
if ! grep -qE '^    image: altatherm-backend:v2-oven-jobs[[:space:]]*$' compose.yaml; then
    echo "The backend image in compose.yaml differs from the expected source image."
    exit 1
fi

dashboard_password=
if ! grep -q '^OVEN_DASHBOARD_USER=' backend.env &&
   ! grep -q '^OVEN_DASHBOARD_PASSWORD=' backend.env; then
    dashboard_password=$(openssl rand -hex 18)
elif ! grep -q '^OVEN_DASHBOARD_USER=.' backend.env ||
     ! grep -q '^OVEN_DASHBOARD_PASSWORD=.' backend.env; then
    echo "Complete the dashboard credentials in backend.env before deploying."
    exit 1
fi

build_dir=$(mktemp -d)
trap 'rm -f "$build_dir/Dockerfile" "$build_dir/oven_api.py"; rmdir "$build_dir"' EXIT
install -m 644 "$files/oven_api.py" "$build_dir/oven_api.py"
printf 'FROM %s\nCOPY oven_api.py /app/oven_api.py\n' "$base_image" > "$build_dir/Dockerfile"
docker build -t "$image" "$build_dir"

backup=$(mktemp ./compose.yaml.before-dashboard.XXXXXX)
cp -p compose.yaml "$backup"
if [ -n "$dashboard_password" ]; then
    printf '\nOVEN_DASHBOARD_USER=viewer\nOVEN_DASHBOARD_PASSWORD=%s\n' "$dashboard_password" >> backend.env
    printf '\nDashboard username: viewer\nDashboard password: %s\nSave this password privately.\n\n' "$dashboard_password"
fi
sed -i "s|^    image: ${base_image}[[:space:]]*$|    image: ${image}|" compose.yaml

if ! docker compose up -d --no-deps --pull never backend ||
   ! curl -fsS --retry 5 --retry-all-errors --retry-delay 1 --max-time 8 \
        http://127.0.0.1:8001/openapi.json |
        grep -F '"/api/oven-dashboard/jobs"' >/dev/null; then
    echo "The new backend did not expose the dashboard route. Restoring the previous image."
    cp -p "$backup" compose.yaml
    docker compose up -d --no-deps --pull never backend
    exit 1
fi

install -d -m 755 "$web" "$web/assets"
install -m 644 "$files/dist/index.html" "$web/index.html"
install -m 644 "$files"/dist/assets/* "$web/assets/"

url=https://metrics-altathermdhi.cloud/oven-dashboard/
curl -fsS --max-time 10 "$url" | grep -F '<title>AltaTherm · Oven jobs</title>' >/dev/null
echo "Dashboard deployed at $url"
