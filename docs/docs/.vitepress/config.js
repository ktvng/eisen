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
        sidebar: [
            {
              text: 'Basic',
              items: [
                { text: 'Types', link: '/intro/types' },
                { text: 'Control Flow', link: '/item-b' },
                { text: 'Functions', link: '/item-b' },
                { text: 'Structs', link: '/item-b' },
                { text: 'Data Structs', link: '/item-b' },
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