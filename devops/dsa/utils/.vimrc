" see :options
" expandtabs
set et
set tabstop=4
" shiftwidth
set sw=4
set nocindent
" autoindent
set ai
" tell indenting programs that we already indented the buffer
let b:did_indent = 1
" don't do an incremental search (don't search before we finish typing)
set nois
" don't ignore case by default
set noic
" don't break at 80 characters
set wrap
" don't add linebreaks at 80 characters
set nolbr
" highlight all search matches
set hls
" default to utf-8
set enc=utf-8
" show the cursor position
set ruler
" allow backspace to go to the previous line
set bs=2
" keep this much history
set history=50
" don't try to maintain vi compatibility
set nocompatible

" syntax highlighting is on
syntax on
" save information for 100 files, with up to 50 lines for each register
set viminfo='100,\"50
if v:lang =~ "utf8$" || v:lang =~ "UTF-8$"
    set fileencodings=utf-8,latin1
endif
