# Cushion

A Django application for browsing and editing CouchDB documents.

 - Server
   - **Add new database**
   - **Browse databases**
   - Databases
      - **Compact**
      - **Empty (delete and recreate)**
      - **Delete**
      - Browse documents
        - **import CSV data**
          - **optionally specify schema to use for data**
          - **optionally specify unique fields (unique and unique_together)**
          - **optionally overwrite/update unique records already stored in the database**
        - **browse raw documents**
        - attachments
          - **display attachments**
          - add
          - delete
          - update
        - create
        - edit
          - **determine form from data types**
          - determine form from predefined Django form
          - dynamically add/remove form fields
        - copy
        - delete
      - Views
        - browse by view
        - UI support for valid view options
        - edit original document
      - Lists
        - browse views
      - Shows
        - browse lists
        - edit original document
      - Changes
        - history of recent edits

See also benoitc's [djangoadmin branch for
couchdbkit](http://github.com/benoitc/couchdbkit/tree/djangoadmin).

Changes to couchdbkit if it's to be used for data import:

 - coercion by schema properties
 - support for a unique_together setting on schemas
 - support for database-less schemas and/or databases per schema rather than databases per Django app.