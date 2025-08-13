FROM postgres:15
COPY ./db/init.sql /docker-entrypoint-initdb.d/
EXPOSE 5432
