const functions = require('@google-cloud/functions-framework');
const { google } = require('googleapis');

/**
 * HTTP Cloud Function Gen2. Query: ?action=start|stop
 * Patches Cloud SQL activationPolicy: ALWAYS (start) or NEVER (stop).
 */
functions.http('setSqlActivation', async (req, res) => {
  const projectId =
    process.env.GCP_PROJECT || process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT;
  const instance = process.env.SQL_INSTANCE;
  const action = req.query.action;

  if (!projectId || !instance) {
    res.status(500).json({ error: 'Missing GCP_PROJECT/GOOGLE_CLOUD_PROJECT or SQL_INSTANCE' });
    return;
  }

  let activationPolicy;
  if (action === 'stop') {
    activationPolicy = 'NEVER';
  } else if (action === 'start') {
    activationPolicy = 'ALWAYS';
  } else {
    res.status(400).json({ error: 'Query param action=start|stop is required' });
    return;
  }

  const auth = new google.auth.GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/cloud-platform'],
  });
  const sqladmin = google.sqladmin({ version: 'v1beta4', auth });

  try {
    const patch = await sqladmin.instances.patch({
      project: projectId,
      instance,
      requestBody: {
        settings: {
          activationPolicy,
        },
      },
    });

    const opName = patch.data?.name;
    if (opName) {
      await waitSqlOperation(sqladmin, projectId, opName);
    }

    res.status(200).json({ ok: true, instance, activationPolicy });
  } catch (e) {
    console.error(e);
    res.status(500).json({
      error: e.message || String(e),
      instance,
      activationPolicy,
    });
  }
});

async function waitSqlOperation(sqladmin, projectId, operationName) {
  const operationId = operationName.split('/').pop();
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    const op = await sqladmin.operations.get({
      project: projectId,
      operation: operationId,
    });
    const status = op.data?.status;
    if (status === 'DONE') {
      if (op.data?.error) {
        const err = op.data.error;
        throw new Error(err.message || JSON.stringify(err));
      }
      return;
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  throw new Error('Timeout waiting for Cloud SQL operation');
}
