# Cushion

A Django application for browsing and editing CouchDB documents.

 - Server
   - Databases
      - Documents
        - import CSV data
          - optionally specify schema to use for data
          - optionally specify unique fields (unique and unique_together)
          - optionally overwrite/update unique records already stored in the database
        - browse raw documents
        - attachments
          - display attachments
          - add
          - delete
          - update
        - create
        - edit
          - determine form from data types
          - determine form from predefined Django form
          - dynamically add/remove form fields
        - copy
        - delete
      - Views
        - edit original document
      - Lists
        - browse views
      - Shows
        - browse lists
        - edit original document
      - Changes

See also benoitc's [djangoadmin branch for
couchdbkit](http://github.com/benoitc/couchdbkit/tree/djangoadmin).