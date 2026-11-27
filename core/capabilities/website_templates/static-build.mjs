import { readFile } from 'node:fs/promises'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer, defineConfig } from 'vite'

// The public page is HTML and CSS. React runs on the build machine only.
export default defineConfig({
  base: './',
  plugins: [{
    name: 'verified-business-page',
    transformIndexHtml: {
      order: 'pre',
      async handler(template) {
        const renderer = await createServer({
          configFile: false,
          appType: 'custom',
          server: { middlewareMode: true, hmr: false, watch: null },
          optimizeDeps: { noDiscovery: true },
        })
        try {
          const { default: App } = await renderer.ssrLoadModule('/src/App.tsx')
          const data = JSON.parse(await readFile('src/business.json', 'utf8'))
          const he = data.language === 'he'
          const title = [data.name, data.category, data.city].filter(Boolean).join(' · ')
          const description = [title, ...data.services.slice(0, 3)].join(' — ')
          const business = {
            '@context': 'https://schema.org',
            '@type': 'LocalBusiness',
            name: data.name, description,
            ...(data.phone && { telephone: data.phone }),
            ...(data.city && { address: {
              '@type': 'PostalAddress', addressLocality: data.city,
              ...(data.address && { streetAddress: data.address }),
            } }),
          }
          const head = renderToStaticMarkup(createElement('title', null, title))
            + renderToStaticMarkup(createElement('meta', { name: 'description', content: description }))
            + '<script type="application/ld+json">'
            + JSON.stringify(business).replaceAll('<', '\\u003c') + '</script>'
          return template.replace('<html>', () => `<html lang="${he ? 'he' : 'en'}" dir="${he ? 'rtl' : 'ltr'}">`)
            .replace('</head>', () => head + '</head>')
            .replace('<!--site-->', () => renderToStaticMarkup(createElement(App)))
        } finally {
          await renderer.close()
        }
      },
    },
  }, {
    name: 'portable-stylesheet',
    transformIndexHtml: {
      order: 'post',
      handler: html => html.replace(/(<link\b[^>]*\brel="stylesheet"[^>]*?) crossorigin\b/g, '$1'),
    },
  }],
})
