import { defineConfig } from 'vitepress';

export default defineConfig({
  title: 'Eisen PL',
  description: 'A modern take on a C++ with a focus on clean and useful abstractions',
  themeConfig: {
    siteTitle: 'Eisen PL',
    socialLinks: [{ icon: 'github', link: 'https://github.com/ktvng/eisen' }],
    nav: [{ text: 'Home', link: '/' }],
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
        ],
      },
      {
        text: 'Memory Model',
        collapsible: true,
        items: [
          { text: 'Pointers', link: '/memory/pointers.md' },
          { text: 'Arrays', link: '/memory/arrays.md' },
          { text: 'Boxes', link: '/memory/boxes.md' },
        ],
      },
      {
        text: 'Inheritance Model',
        collapsible: true,
        items: [
          { text: 'Overview', link: '/abstraction/overview.md' },
          {
            text: 'Member Functions',
            link: '/abstraction/member_functions.md',
          },
          { text: 'Interfaces', link: '/abstraction/interfaces.md' },
          {
            text: 'Embedded Structs',
            link: '/abstraction/embedded_structs.md',
          },
          { text: 'Variants', link: '/abstraction/variants.md' },
          { text: 'Casting', link: '/abstraction/casting.md' },
        ],
      },
    ],
  },
  markdown: {
    theme: {
      light: 'vitesse-light',
      dark: 'vitesse-dark',
    },
    shikiSetup: (shiki) => {
      shiki.loadLanguage({
        "version": "0.0.1",
        "filetypes": [
          ".en",
          ".ei"
        ],
        "name": "eisen",
        "scopeName": "source.eisen",
        "repository": {
          "keywords": {
            "patterns": [
              {
                "name": "keyword.control.eisen",
                "match": "\\b(if|else|while|for|return)\\b"
              }
            ]
          },
          "strings": {
            "name": "string.quoted.double.eisen",
            "begin": "\"",
            "end": "\"",
            "patterns": [
              {
                "name": "constant.character.escape.eisen",
                "match": "\\\\."
              }
            ]
          },
          "comments": {
            "patterns": [
              {
                "comment": "documentation comments",
                "name": "comment.line.documentation.rust",
                "match": "^\\s*///.*"
              },
              {
                "comment": "line comments",
                "name": "comment.line.double-slash.rust",
                "match": "\\s*//.*"
              }
            ]
          }
        },
        "patterns": [
          {
            "include": "#keywords"
          },
          {
            "include": "#strings"
          },
          {
            "include": "#comments"
          },
          {
            "comment": "support.function.builtin.eisen",
            "name": "support.function.builtin.python",
            "match": "\\b(print|println)\\b"
          },
          {
            "comment": "storage keywords",
            "name": "keyword.other.rust storage.type.rust",
            "match": "\\b(mod)\\b"
          },
          {
            "comment": "function/method calls, chaining",
            "name": "meta.function.call.rust",
            "begin": "((?:r#(?!crate|[Ss]elf|super))?[A-Za-z0-9_]+)(\\()",
            "beginCaptures": {
              "1": {
                "name": "entity.name.function.rust"
              },
              "2": {
                "name": "punctuation.brackets.round.rust"
              }
            },
            "end": "\\)",
            "endCaptures": {
              "0": {
                "name": "punctuation.brackets.round.rust"
              }
            },
            "patterns": [
              {
                "include": "#block-comments"
              },
              {
                "include": "#comments"
              },
              {
                "include": "#keywords"
              },
              {
                "include": "#lvariables"
              },
              {
                "include": "#constants"
              },
              {
                "include": "#gtypes"
              },
              {
                "include": "#functions"
              },
              {
                "include": "#lifetimes"
              },
              {
                "include": "#macros"
              },
              {
                "include": "#namespaces"
              },
              {
                "include": "#punctuation"
              },
              {
                "include": "#strings"
              },
              {
                "include": "#types"
              },
              {
                "include": "#variables"
              }
            ]
          },
          {
            "name": "keyword.declaration.struct.rust storage.type.rust",
            "match": "\\b(?<!\\.)(struct|data struct)\\b"
          },
          {
            "comment": "fn",
            "name": "keyword.other.fn.rust",
            "match": "\\bfn\\b"
          },
          {
            "comment": "dashrocket, skinny arrow",
            "name": "keyword.operator.arrow.skinny.rust",
            "match": "->"
          },
          {
            "comment": "namespace operator",
            "name": "keyword.operator.namespace.rust",
            "match": "::"
          },
          {
            "comment": "constant.numeric.eisen",
            "match": "\\b\\d+(.?\\d*)?\\b",
            "name": "constant.numeric.python"
          },
          {
            "comment": "assignment operators",
            "name": "keyword.operator.assignment.rust",
            "match": "(\\+=|-=|\\*=|/=|%=|\\^=|&=|\\|=|<<=|>>=)"
          },
          {
            "comment": "single equal",
            "name": "keyword.operator.assignment.equal.rust",
            "match": "(?<![<>])=(?!=|>)"
          },
          {
            "comment": "comparison operators",
            "name": "keyword.operator.comparison.rust",
            "match": "(=(=)?(?!>)|!=|<=|(?<!=)>=)"
          },
          {
            "comment": "math operators",
            "name": "keyword.operator.math.rust",
            "match": "(([+%]|(\\*(?!\\w)))(?!=))|(-(?!>))|(/(?!/))"
          },
          {
            "comment": "storage keywords",
            "name": "support.function.builtin.python",
            "match": "\\b(let|var|embed|inherits)\\b"
          },
          {
            "comment": "constant.language.eisen",
            "match": "\\b(true|false)\\b",
            "name": "constant.language.python"
          }
        ]
      })
    },
  },
});
