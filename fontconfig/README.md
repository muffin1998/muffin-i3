# FontConfig 

## Usage

```shell script
cp fontconfig/fonts.conf ~/.config/fontconfig/
```

The config file change the default fonts for displaying English and Chinese. Add any other fonts in ```<prefer>``` tag as you like, as the fontconfig will auto select font to meet the requirement, is to say, the next font will be selected if the current one doesn't support the characters.

Note: Setting the value of property "binding" to "strong" is required in non-latin locale (I guess), assume the current locale is zh_CN.UTF-8, the font pattern send by application, which contains some font properties and is used for matching fonts in system,  will be added the property "lang=zh-CN" by fontconfig, if the "family" value was binding as "weak" (by default), the priority of property "lang" is higher than property "family", cause the Chinese font will be picked first no matter showing English or Chinese.

## See also

[Fonts - ArchWiki](https://wiki.archlinux.org/index.php/fonts)

[FontConfig User Documentation](http://fontconfig.org/fontconfig-user.html)