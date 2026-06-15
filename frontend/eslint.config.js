import js from '@eslint/js';
import ts from 'typescript-eslint';
import svelte from 'eslint-plugin-svelte';
import prettier from 'eslint-config-prettier';
import globals from 'globals';
import tailwind from 'eslint-plugin-tailwindcss';

/** @type {import('eslint').Linter.Config[]} */
export default [
  js.configs.recommended,
  ...ts.configs.recommended,
  ...svelte.configs['flat/recommended'],
  prettier,
  ...svelte.configs['flat/prettier'],
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
    },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts'],
    languageOptions: {
      parserOptions: {
        parser: ts.parser,
      },
    },
    rules: {
      // TypeScript handles undefined-symbol checks (incl. generic type params).
      'no-undef': 'off',
    },
  },
  {
    ...tailwind.configs.recommended,
    files: ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx', '**/*.svelte'],
    settings: {
      tailwindcss: {
        cssConfigPath: 'src/app.css',
      },
    },
    rules: {
      // Only the rules that add value without DaisyUI false positives
      'tailwindcss/no-unnecessary-arbitrary-value': 'warn',
      'tailwindcss/enforces-shorthand': 'warn',
      'tailwindcss/no-contradicting-classname': 'error',
      // Disabled: flags DaisyUI/custom classes as unknown
      'tailwindcss/no-custom-classname': 'off',
      // Disabled: prettier handles class ordering
      'tailwindcss/classnames-order': 'off',
      'tailwindcss/enforces-negative-arbitrary-values': 'off',
      'tailwindcss/no-arbitrary-value': 'off',
    },
  },
  {
    ignores: ['dist/', '.vite/', 'src/services/api-types.ts'],
  },
];
