**NOTE : this library somehow works, but it is not maintained, unfinished, very inefficient, not packaged properly and not Django-ish ...**


## [Documentation-index](http://django-cube.googlecode.com/hg/doc/_build/index.html) ##
> ### [Quick-start](http://django-cube.googlecode.com/hg/doc/_build/quick_start.html) ###
> ### [Some snippets](http://django-cube.googlecode.com/hg/doc/_build/snippets.html) ###

## Introduction ##

Say I have a bookcase, with nice books on it... And I want to create a "bookcase" application with my favorite framework.

That's my model

```
from django.db import models

class Book (models.Model):
    title = models.CharField(max_length=100)
    genre = models.CharField(max_length=100)
```

<table>
<tr>
<td><img src='http://django-cube.googlecode.com/hg/doc/googlecode/bookcase.png' width='400'><td />
<td>

I would like to calculate some statistics on my books, for example counting them :<br>
<br>
<table><thead><th>                      </th><th> <b>philosophy</b> </th><th> <b>food</b>       </th><th> <b>novels</b>     </th></thead><tbody>
<tr><td> <b>A-M</b>                </td><td> <i>how many ??</i></td><td> <i>how many ??</i></td><td> <i>how many ??</i></td></tr>
<tr><td> <b>N-Z</b>                </td><td> <i>how many ??</i></td><td> <i>how many ??</i></td><td> <i>how many ??</i></td></tr></tbody></table>

<table>
<tr>
<td><img src='https://django-cube.googlecode.com/hg/doc/googlecode/left-arrow.gif' width='80'><td />
<td>
But that's such a pain, because I have to count on the whole bookcase !!!</td>
<tr />
<table />

<pre><code>    Book.objects.filter(genre="novels")#etc, etc ...<br>
</code></pre>

Even in real life that wouldn't be very practical ...<br>
<br>
<td />
<tr />
<table />

<table>
<tr>
<td>
<img src='http://django-cube.googlecode.com/hg/doc/googlecode/bookcase_ordered.png' width='400'>
<td />
<td>

<table>
<tr>
<td><img src='https://django-cube.googlecode.com/hg/doc/googlecode/left-arrow.gif' width='80'><td />
<td>
What is much more clever is to classify my books into several boxes. So instead of counting on the whole bookcase, I can count on each box !!!</td>
<tr />
<table />

<pre><code>from cube.models import Cube<br>
<br>
class BookCaseCube(Cube):<br>
<br>
    genre = Dimension('genre')<br>
    first_letter_title = Dimension('title__iregex', sample_space=[r'^[a-n].*', r'^[m-z].*'])<br>
<br>
    @staticmethod<br>
    def aggregation(queryset):<br>
        return queryset.count()<br>
</code></pre>

That's actually the aim of django-cube. Here, we defined :<br>
<ul><li>2 dimensions (<i><b>genre</b></i> and <i><b>first_letter_title</b></i>) : they actually define our "boxes"<br>
</li><li>the <i><b>aggregation</b></i> method : corresponds with the operation to apply on each "box" (<i>count</i> in our case), with <i><b>queryset</b></i> corresponding to the base queryset of the "box" !</li></ul>

<td />
<tr />
<table />