/**
 * Script to convert SVG images to PNG for social media sharing
 *
 * Usage:
 *   npm install sharp
 *   node scripts/convert-images.js
 */

const fs = require('fs');
const path = require('path');

async function convertImages() {
  try {
    // Dynamic import for sharp (ES module)
    const sharp = (await import('sharp')).default;

    const publicDir = path.join(__dirname, '../public');

    const conversions = [
      {
        input: path.join(publicDir, 'og-image.svg'),
        output: path.join(publicDir, 'og-image.png'),
        width: 1200,
        height: 630,
      },
      {
        input: path.join(publicDir, 'twitter-image.svg'),
        output: path.join(publicDir, 'twitter-image.png'),
        width: 1200,
        height: 600,
      },
    ];

    console.log('Converting SVG images to PNG...\n');

    for (const conversion of conversions) {
      if (fs.existsSync(conversion.input)) {
        await sharp(conversion.input)
          .resize(conversion.width, conversion.height)
          .png({ quality: 100 })
          .toFile(conversion.output);

        console.log(`✓ Converted: ${path.basename(conversion.input)} → ${path.basename(conversion.output)}`);
      } else {
        console.log(`✗ File not found: ${conversion.input}`);
      }
    }

    console.log('\n✓ All images converted successfully!');
    console.log('\nNext steps:');
    console.log('1. Verify images at /public/og-image.png and /public/twitter-image.png');
    console.log('2. Test with https://www.opengraph.xyz/');
    console.log('3. Deploy and verify meta tags');

  } catch (error) {
    if (error.code === 'ERR_MODULE_NOT_FOUND' || error.message.includes('sharp')) {
      console.log('Sharp not installed. Installing...\n');
      console.log('Run: npm install sharp');
      console.log('Then run this script again: node scripts/convert-images.js');
    } else {
      console.error('Error converting images:', error);
    }
  }
}

convertImages();
