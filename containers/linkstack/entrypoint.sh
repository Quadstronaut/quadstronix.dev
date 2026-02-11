#!/bin/sh

# Check if symfony/yaml is missing
if [ ! -d "/htdocs/vendor/symfony/yaml" ]; then
    echo "symfony/yaml not found, installing..."
    cd /htdocs
    export COMPOSER_HOME=/tmp/composer
    php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
    php composer-setup.php --quiet
    ./composer.phar require symfony/yaml --quiet
    rm composer-setup.php composer.phar
    echo "symfony/yaml installed successfully"
fi

# Execute the original entrypoint
exec /entrypoint "$@"
