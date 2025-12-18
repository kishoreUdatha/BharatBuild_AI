/**
 * Setup E2E Test Users
 * Creates test users in the backend for E2E testing
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api/v1';

const testUsers = [
  {
    email: 'test@example.com',
    password: 'TestPassword123!',
    full_name: 'Test User',
    role: 'developer'
  },
  {
    email: 'freeuser@example.com',
    password: 'TestPassword123!',
    full_name: 'Free Test User',
    role: 'developer'
  },
  {
    email: 'premiumuser@example.com',
    password: 'TestPassword123!',
    full_name: 'Premium Test User',
    role: 'developer'
  },
  {
    email: 'userA@example.com',
    password: 'TestPassword123!',
    full_name: 'User A',
    role: 'developer'
  },
  {
    email: 'userB@example.com',
    password: 'TestPassword123!',
    full_name: 'User B',
    role: 'developer'
  }
];

async function createUser(user) {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(user),
    });

    const data = await response.json();

    if (response.ok) {
      console.log(`[OK] Created user: ${user.email}`);
      return { success: true, email: user.email };
    } else if (response.status === 400 && data.detail?.includes('already')) {
      console.log(`[SKIP] User already exists: ${user.email}`);
      return { success: true, email: user.email, skipped: true };
    } else {
      console.log(`[FAIL] Failed to create user: ${user.email} - ${data.detail || JSON.stringify(data)}`);
      return { success: false, email: user.email, error: data.detail };
    }
  } catch (error) {
    console.log(`[ERROR] Error creating user: ${user.email} - ${error.message}`);
    return { success: false, email: user.email, error: error.message };
  }
}

async function main() {
  console.log('='.repeat(60));
  console.log('Setting up E2E Test Users');
  console.log(`API: ${API_BASE_URL}`);
  console.log('='.repeat(60));
  console.log('');

  const results = [];

  for (const user of testUsers) {
    const result = await createUser(user);
    results.push(result);
  }

  console.log('');
  console.log('='.repeat(60));
  console.log('Summary:');
  const created = results.filter(r => r.success && !r.skipped).length;
  const skipped = results.filter(r => r.success && r.skipped).length;
  const failed = results.filter(r => !r.success).length;
  console.log(`  Created: ${created}`);
  console.log(`  Skipped (already exist): ${skipped}`);
  console.log(`  Failed: ${failed}`);
  console.log('='.repeat(60));

  if (failed > 0) {
    process.exit(1);
  }
}

main();
