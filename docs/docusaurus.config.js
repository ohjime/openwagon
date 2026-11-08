// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const lightCodeTheme = require('prism-react-renderer').themes.vsLight;
const darkCodeTheme = require('prism-react-renderer').themes.vsDark;

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Waygon',
  tagline: 'Waygon Developer Guide',
  url: 'https://ohjime.github.io',
  baseUrl: '/waygon/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.ico',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'ohjime', // Usually your GitHub org/user name.
  projectName: 'waygon', // Usually your repo name.
  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  
  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/ohjime/waygon/tree/main/docs/',
          breadcrumbs: true,
          admonitions: true,
          showLastUpdateTime: true,
        },
        theme: {
          customCss: [
            require.resolve('./src/css/custom.css'),
            require.resolve('./src/css/mermaid-dark.css'),
          ],
        },
      }),
    ],
  ],

  themes: ['@docusaurus/theme-mermaid'],

  markdown: {
    mermaid: true,
    format: 'detect',
    
  },

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      docs: {
        sidebar: {
          autoCollapseCategories: true,
        },
      },
      navbar: {
        title: 'Waygon',
        logo: {
          alt: 'Logo',
          src: 'img/logo.png',
        },
        items: [
          {
            type: 'doc',
            docId: 'manual/start',
            position: 'left',
            label: 'User Guide',
            sidebar: null, // Hide sidebar for this doc
          },
          {
            type: 'doc',
            docId: 'design/index',
            position: 'right',
            label: 'Design',
          },
          {
            type: 'doc',
            docId: 'development/index',
            position: 'right',
            label: 'Development',
          },
          {
            label: 'Backlog',
            href: 'https://tree.taiga.io/project/ohjime-waygon/backlog',
            position: 'right',
          },
          {
            href: 'https://github.com/ohjime/waygon/',
            position: 'right',
            className: 'navbar-github-icon',
            'aria-label': 'GitHub repository',
          },
        ],
      },
      footer: {
        links: [
          
          {
            title: 'Resources',
            items: [
              {
                label: 'Blog',
                href: '#',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/ohjime/waygon/tree/main/',
              },
            ],
          },
        ],
      },
      prism: {
        additionalLanguages: ['bash', 'dart', 'yaml'],
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
      },
      mermaid: {
        theme: {
          light: 'neutral',
          dark: 'forest',
        },
      },
    }),
};

module.exports = config;
