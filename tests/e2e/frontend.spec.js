const { test, expect } = require('@playwright/test');

test('login, pestañas, búsqueda, ficha y volver', async ({ page }) => {
  const consoleErrors = [];
  page.on('console', message => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', error => consoleErrors.push(error.message));

  await page.goto('/');
  await page.locator('input[name="login"]').fill('admin');
  await page.locator('input[name="password"]').fill('Admin-Demo-2026!');
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();

  await expect(page.getByRole('heading', { name: 'Servicios', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Organización' }).click();
  await expect(page.getByRole('heading', { name: 'Organización' })).toBeVisible();
  await page.getByRole('button', { name: 'Editar' }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog').getByRole('heading')).toContainText('Editar');
  const orgName = page.getByRole('dialog').locator('input[name="nombre"]');
  const originalOrgName = await orgName.inputValue();
  await orgName.fill(`${originalOrgName} E2E`);
  await page.getByRole('dialog').getByRole('button', { name: 'Guardar' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await expect(page.locator('#orgbody')).toContainText(`${originalOrgName} E2E`);
  await page.getByRole('button', { name: 'Editar' }).first().click();
  await page.getByRole('dialog').locator('input[name="nombre"]').fill(originalOrgName);
  await page.getByRole('dialog').getByRole('button', { name: 'Guardar' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await expect(page.locator('#orgbody')).toContainText(originalOrgName);
  await page.getByRole('button', { name: 'Usuarios' }).click();
  await expect(page.getByRole('heading', { name: 'Usuarios' })).toBeVisible();
  await page.getByRole('button', { name: 'Editar' }).first().click();
  await expect(page.getByRole('dialog').getByRole('heading')).toHaveText('Editar usuario');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancelar' }).click();
  await page.getByRole('button', { name: 'Catálogos' }).click();
  await expect(page.getByRole('heading', { name: 'Catálogos controlados' })).toBeVisible();
  await page.getByRole('button', { name: 'Editar' }).first().click();
  await expect(page.getByRole('dialog').getByRole('heading')).toHaveText('Editar catálogo');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancelar' }).click();
  await page.getByRole('button', { name: 'Importaciones' }).click();
  await expect(page.getByRole('heading', { name: 'Importaciones' })).toBeVisible();
  await page.getByRole('button', { name: 'Servicios', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Servicios', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Niveles 1' }).click();
  await expect(page.getByRole('dialog').getByRole('heading')).toHaveText('Servicios Nivel 1');
  await expect(page.getByRole('dialog').locator('tbody')).toContainText('SE.12');
  await page.getByRole('dialog').getByRole('button', { name: 'Editar' }).first().click();
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Guardar cambios' })).toBeVisible();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancelar edición' }).click();
  await page.locator('#modalClose').click();

  await page.locator('input[name="q"]').fill('SE.12.3');
  await page.getByRole('button', { name: 'Buscar' }).click();
  await expect(page.locator('tbody')).toContainText('SE.12.3');
  await page.getByRole('button', { name: 'Ver' }).click();
  await expect(page.locator('#content h2')).toContainText('SE.12.3');
  await expect(page.locator('#content')).toContainText('Código original:');
  await expect(page.locator('#content')).toContainText('Sección responsable:');
  await expect(page.locator('#content')).toContainText('Usuario responsable:');
  await expect(page.locator('#content')).toContainText('Origen:');
  await page.getByRole('button', { name: 'Editar' }).click();
  await expect(page.getByRole('dialog').getByRole('heading')).toHaveText('Editar servicio');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancelar' }).click();
  await page.getByRole('button', { name: 'Volver' }).click();
  await expect(page.getByRole('heading', { name: 'Servicios', exact: true })).toBeVisible();
  expect(consoleErrors.filter(message => !message.includes('401 (Unauthorized)'))).toEqual([]);
});
