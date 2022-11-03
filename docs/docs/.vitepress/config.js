// export default {
//     markdown: {
//         theme: 'nord',
//         lineNumbers: true
//     }
// }

import { defineConfig } from 'vitepress'

export default defineConfig({
    title: "stanza language",
    themeConfig: {
        sidebar: [
            {
              text: 'Section Title A',
              items: [
                { text: 'Item A', link: '/item-a' },
                { text: 'Item B', link: '/item-b' },
              ]
            },
            {
              text: 'Section Title B',
              items: [
                { text: 'Item C', link: '/item-c' },
                { text: 'Item D', link: '/item-d' },
              ]
            }
          ]
    },
    markdown: {
        theme: 'material-ocean',
    }
})