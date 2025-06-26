ATTRIBUTES_TO_ALLOW = {
    'href': True,
    'target': True,
    'rel': True,
    'class': True,
    'aria-label': True,
    'data-*': True,
    'id': True,
    'type': True,
    'data-bs-toggle': True,
    'data-bs-target': True,
    'aria-expanded': True,
    'aria-controls': True,
    'aria-labelledby': True,
}

CKEDITOR_5_CONFIGS = {
    'ddm_ckeditor':  {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': [
            'heading', '|',
            'alignment', 'outdent', 'indent', '|',
            'bold', 'italic', 'underline', 'link', 'highlight', '|',
            {
                'label': 'Fonts',
                'icon': 'text',
                'items': ['fontSize', 'fontFamily', 'fontColor']
            }, '|',
            'bulletedList', 'numberedList', 'insertTable', 'blockQuote', 'code', 'removeFormat', '|',
            'insertImage', 'fileUpload', 'mediaEmbed', '|',
            'sourceEditing'
        ],
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter', 'imageStyle:side',  '|'],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ]
        },
        'table': {
            'contentToolbar': ['tableColumn', 'tableRow', 'mergeTableCells',
                               'tableProperties', 'tableCellProperties'],
        },
        'heading': {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        },
        'htmlSupport': {
            'allow': [
                {
                    'name': 'video',
                    'attributes': {
                        'height': True,
                        'width': True,
                        'controls': True,
                    },
                    'styles': True
                },
                {
                    'name': 'p',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'span',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'div',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'a',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'table',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'td',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'th',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'button',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'h1',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'h2',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
            ],
            'disallow': []
        },
        'wordCount': {
            'displayCharacters': False,
            'displayWords': False,
        }
    },
    'default': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': [
            'heading', '|',
            'alignment', 'outdent', 'indent', '|',
            'bold', 'italic', 'underline', 'link', 'highlight', '|',
            {
                'label': 'Fonts',
                'icon': 'text',
                'items': ['fontSize', 'fontFamily', 'fontColor']
            }, '|',
            'bulletedList', 'numberedList', 'insertTable', 'blockQuote', 'code', 'removeFormat', '|',
            'insertImage', 'fileUpload', 'mediaEmbed', '|',
            'sourceEditing'
        ],
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter', 'imageStyle:side', '|'],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ]
        },
        'table': {
            'contentToolbar': ['tableColumn', 'tableRow', 'mergeTableCells',
                               'tableProperties', 'tableCellProperties'],
        },
        'heading': {
            'options': [
                {'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph'},
                {'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1'},
                {'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2'},
                {'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3'}
            ]
        },
        'htmlSupport': {
            'allow': [
                {
                    'name': 'video',
                    'attributes': {
                        'height': True,
                        'width': True,
                        'controls': True,
                    },
                    'styles': True
                },
                {
                    'name': 'p',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'span',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'div',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'a',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'table',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'td',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'th',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'button',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'h1',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
                {
                    'name': 'h2',
                    'attributes': ATTRIBUTES_TO_ALLOW
                },
            ],
            'disallow': []
        },
        'wordCount': {
            'displayCharacters': False,
            'displayWords': False,
        }
    }
}