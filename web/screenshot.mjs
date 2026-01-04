import { chromium } from 'playwright';

const args = process.argv.slice(2);
const darkMode = args.includes('--dark');
const mobileOnly = args.includes('--device=iphone');
const urlArg = args.find(arg => !arg.startsWith('--'));
const url = urlArg || 'http://localhost:5173';

const suffix = darkMode ? '-dark' : '';

const browser = await chromium.launch();

// Desktop screenshot (unless mobile-only mode)
if (!mobileOnly) {
  const desktopContext = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: darkMode ? 'dark' : 'light'
  });
  const desktopPage = await desktopContext.newPage();
  await desktopPage.goto(url);
  await desktopPage.waitForLoadState('networkidle');
  await desktopPage.screenshot({ path: `/tmp/scapin-desktop${suffix}.png`, fullPage: false });
  console.log(`Desktop screenshot saved to /tmp/scapin-desktop${suffix}.png`);
  await desktopContext.close();
}

// Mobile screenshot - create fresh context with mobile viewport
const mobileContext = await browser.newContext({
  viewport: { width: 390, height: 844 },
  colorScheme: darkMode ? 'dark' : 'light',
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true
});
const mobilePage = await mobileContext.newPage();
await mobilePage.goto(url);
await mobilePage.waitForLoadState('networkidle');
await mobilePage.screenshot({ path: `/tmp/scapin-mobile${suffix}.png`, fullPage: false });
console.log(`Mobile screenshot saved to /tmp/scapin-mobile${suffix}.png`);
await mobileContext.close();

await browser.close();
