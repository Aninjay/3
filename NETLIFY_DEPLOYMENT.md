# Deploying the TAPMI frontend on Netlify

Netlify builds the React/Vite frontend in `frontend/dist`. It does not start the Flask API or provide the PostgreSQL database. The frontend needs a separately deployed Flask API before sign-in and other server-backed features can work.

## Connect the frontend to the API

1. Deploy the Flask backend on a service that can run this repository's `Dockerfile` or Docker Compose stack, and connect it to a persistent PostgreSQL database. Use a unique `SECRET_KEY`, set `SEED_DEMO_DATA=false`, and configure `BOOTSTRAP_CONVENER_EMAIL` plus a unique `BOOTSTRAP_CONVENER_PASSWORD` (minimum 12 characters) for the first organizer login.
2. Check that `https://YOUR_API_HOST/api/v1/health` returns JSON with `status: "healthy"` and `database.connected: true`.
3. Set the backend's `CORS_ORIGINS` environment variable to the exact Netlify site origin, such as `https://your-site-name.netlify.app` (no trailing slash or path). This allows the browser frontend to call the API.

4. In the Netlify site's environment variable settings, add this variable with the **Builds** scope enabled:

   ```text
   VITE_API_BASE_URL=https://YOUR_API_HOST/api/v1
   ```

   Use the API's public HTTPS origin and include `/api/v1`. This value is a public API address, not a secret.

5. Trigger a new Netlify deploy. Vite embeds `VITE_*` values during the build, so changing the variable requires rebuilding the site.

Local development can leave `VITE_API_BASE_URL` unset; the frontend then uses `/api/v1`, which Vite proxies to the local Flask server on port 5001. Docker explicitly sets `PORT=5000` for the container and is unaffected.

If the API health check succeeds but browser sign-in still fails, check the browser console for a CORS error and confirm the backend allows the Netlify site's origin. Also ensure the deployed database has been migrated and contains the account you are trying to use; Netlify does not share the local development database.
