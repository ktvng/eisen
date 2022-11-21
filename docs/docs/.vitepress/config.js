// export default {
//     markdown: {
//         theme: 'nord',
//         lineNumbers: true
//     }
// }

import { defineConfig } from 'vitepress'

export default defineConfig({
    title: "Eisen PL",
    themeConfig: {
        siteTitle: "Eisen PL",
        socialLinks: [
          { icon: 'github', link: 'https://github.com/ktvng/eisen' },
        ],
        nav: [
          { text: 'Home', link: '/' }
        ],
        sidebar: [
            {
              text: 'Introduction',
              items: [
                { text: 'Syntax 101', link: '/intro/syntax' },
                { text: 'Functions', link: '/intro/functions' },
                { text: 'Structs', link: '/intro/structs' },
                { text: 'Variables', link: '/intro/variables' },
                { text: 'Data Structs', link: '/intro/data_structs.md' },
              ]
            },
            {
              text: 'Memory Model',
              items: [
                { text: 'Variables/Pointers', link: '/item-b' },
                { text: 'Values', link: '/item-b' },
                { text: 'Boxes', link: '/item-b' },
              ]
            },
            {
              text: 'Inheritance Model',
              items: [
                { text: 'Member Functions', link: '/item-b' },
                { text: 'Embedded Structs', link: '/item-b' },
                { text: 'Interfaces', link: '/item-b' },
                { text: 'Casting', link: '/item-b' },
                { text: 'Variants', link: '/item-b' },
              ]
            },
            {
              text: 'Functional',
              items: [
                { text: 'Extensions', link: '/item' },
                { text: 'Lambdas', link: '/item' },
                { text: 'Multiple Dispatch', link: '/item' },
                { text: 'Inline', link: '/item' },
              ]
            }
          ]
    },
    markdown: {
        theme: 'vitesse-dark',
    }
})