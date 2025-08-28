module.exports = {
  extends: [
    'stylelint-config-standard',
    'stylelint-prettier/recommended',
  ],
  rules: {
    // Property order and formatting
    'declaration-empty-line-before': null,
    'property-no-vendor-prefix': null,
    'value-no-vendor-prefix': null,
    
    // CSS custom properties
    'custom-property-pattern': '^[a-z][a-z0-9]*(-[a-z0-9]+)*$',
    
    // Class and ID naming convention - allow existing patterns
    'selector-class-pattern': null,
    'selector-id-pattern': null,
    'keyframes-name-pattern': null,
    
    // Font family names
    'font-family-name-quotes': 'always-where-recommended',
    
    // Units and values
    'length-zero-no-unit': true,
    
    // Selectors
    'selector-pseudo-element-colon-notation': 'double',
    'selector-type-case': 'lower',
    
    // Functions
    'function-name-case': 'lower',
    'function-url-quotes': 'always',
    
    // Comments
    'comment-empty-line-before': [
      'always',
      {
        except: ['first-nested'],
        ignore: ['stylelint-commands'],
      },
    ],
    
    // At-rules
    'at-rule-empty-line-before': [
      'always',
      {
        except: ['blockless-after-same-name-blockless', 'first-nested'],
        ignore: ['after-comment'],
      },
    ],
    
    // No duplicate properties
    'declaration-block-no-duplicate-properties': true,
    
    // Shorthand properties
    'declaration-block-no-redundant-longhand-properties': true,
    
    // Vendor prefixes (allow them for browser compatibility)
    'property-no-vendor-prefix': [
      true,
      {
        ignoreProperties: [
          'background-clip',
          'text-fill-color',
          'appearance',
          'transform',
          'transition',
          'animation',
        ],
      },
    ],
    
    // Browser specific rules
    'selector-pseudo-class-no-unknown': [
      true,
      {
        ignorePseudoClasses: ['global'],
      },
    ],

    // Allow descending specificity for intentional overrides
    'no-descending-specificity': null,
  },
};