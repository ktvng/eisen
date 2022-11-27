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
              collapsible: true,
              items: [
                { text: 'Syntax 101', link: '/intro/syntax' },
                { text: 'Functions', link: '/intro/functions' },
                { text: 'Structs', link: '/intro/structs' },
                { text: 'Variables', link: '/intro/variables' },
                { text: 'Data Structs', link: '/intro/data_structs.md' },
                { text: 'Modules', link: '/intro/modules.md' },
              ]
            },
            {
              text: 'Memory Model',
              collapsible: true,
              items: [
                { text: 'Pointers', link: '/memory/pointers.md' },
                { text: 'Arrays', link: '/memory/arrays.md' },
                { text: 'Boxes', link: '/item-b' },
              ]
            },
            {
              text: 'Inheritance Model',
              collapsible: true,
              items: [
                { text: 'Overview', link: '/abstraction/overview.md' },
                { text: 'Member Functions', link: '/abstraction/member_functions.md' },
                { text: 'Interfaces', link: '/abstraction/interfaces.md' },
                { text: 'Embedded Structs', link: '/abstraction/embedded_structs.md' },
                { text: 'Casting', link: '/item-b' },
                { text: 'Variants', link: '/item-b' },
              ]
            },
            {
              text: 'Functional',
              collapsible: true,
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