*** Settings ***
Resource        table_resource.robot

Suite Setup     Go To Page "tables/tables.html"

Test Tags       known issue internet explorer
