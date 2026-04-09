# Use an official Apache httpd image as a parent image
FROM httpd:2.4

# Copy the static content (index.html, index.js) into the Apache server's document root directory
COPY ./index.html /usr/local/apache2/htdocs/index.html
COPY ./index.js /usr/local/apache2/htdocs/index.js

# Expose port 80
EXPOSE 80